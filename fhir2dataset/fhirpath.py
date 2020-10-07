"""set of functions allowing to use the javascript coded library on the repository https://github.com/HL7/fhirpath.js
"""  # noqa
import os
import json
import logging
from subprocess import Popen, PIPE
from typing import List


logger = logging.getLogger(__name__)

wrapper = """
(function run(globals) {
    try {
        let result = (%(func)s).apply(globals, %(args)s);
        if ((typeof result) == 'string') {
            result = JSON.stringify(result);
        }
        console.log(
            %(result_keyword)s +
            JSON.stringify({"result": result}) +
            %(result_keyword)s
            );
    } catch (e) {
        console.log(
            %(result_keyword)s +
            JSON.stringify({error: e.message}) +
            %(result_keyword)s
            );
    }
})(%(globals)s);
"""


def execute(code: str, args: list = None, g: dict = None):
    """Function to execute code written in javascript

    Args:
        code (str): javascript code
        args (list, optional): the arguments that the js code takes as input. Defaults to None.
        g (dict, optional): the 'this' object in the code. Defaults to None.

    Returns:
        dict or list: result of the js script
    """
    if args is None:
        args = []

    if g is None:
        g = {}

    assert isinstance(code, str)
    assert isinstance(g, dict)
    assert code.strip(" ").strip("\t").startswith("function"), "Code must be function"

    # Here, the Popen function allows to execute the javascript script as in a terminal with the
    # command 'node'. As in a terminal, the result is returned in console between the keywords
    # defined by the variable VV. The python script, is in charge of retrieving the result between
    # these keywords.
    path = os.path.join(os.path.dirname(__file__), "metadata")

    prc = Popen(
        "node", shell=False, stderr=PIPE, stdout=PIPE, stdin=PIPE, cwd=path, encoding="utf-8"
    )

    result_keyword = "--FHIRPATH--"

    c = wrapper % {
        "func": code,
        "globals": json.dumps(g),
        "args": json.dumps(args),
        "result_keyword": f'"{result_keyword}"',
    }
    outs, errs = prc.communicate(input=c)
    if isinstance(outs, str):
        outs = outs.split(result_keyword)[1]
        outs = json.loads(outs)
    if "result" in outs:
        outs = outs["result"]
        return outs
    elif "error" in outs:
        raise Exception((outs.get("error"), errs))
    else:
        raise Exception(errs)


def parse_fhirpath(fhirpath: str):
    result = execute(
        """function test(fhirpath){
        const fhirpath_module = require("fhirpath");
        return JSON.stringify(fhirpath_module.parse(fhirpath))
    }
    """,
        args=[fhirpath],
    )
    return result


def fhirpath_processus_tree(forest_dict, resource):
    result = execute(
        """function test(args){
            const graph = require('./forest')
            forest_dict = args[0]
            resource = args[1]
            let result = []
            for (const [root_id, tree_raw] of Object.entries(forest_dict)) {
                nodes_dict_raw = tree_raw["nodes_dict"]
                edges_array_raw = tree_raw["edges_array"]
                graph.compute_fhirpaths(nodes_dict_raw, edges_array_raw, root_id, resource, result)
            }
            return result
        }
        """,
        args=[[forest_dict, resource]],
    )
    return result


def multiple_search_dict(resources: list, elements: dict) -> List[dict]:
    """Returns the updated element instance on each element in the Resources list. These updated
    instances are stored in a list which is the element returned by the function.
    The update consists for each element of the instance elements in the application of the fhirpath
    (element.fhirpath) on an instance of the Resources list and the storage of the response in element.value.

    Args:
        resources (list): list composed of several instances of resources
        elements (dict): an instance of the Elements object in dictionary format

    Returns:
        list: elements object list copied and updated on each resource composing the resources list
    """  # noqa
    result = execute(
        """function test(resources) {
                const fhirpath = require("fhirpath");
                const fhirpath_r4_model = require("fhirpath/fhir-context/r4");

                return resources.map((resource) => {
                    var fhirpath_result = [];
                    for (index = 0; index < this.elements.length; index++) {
                        try {
                            this.elements[index].value = fhirpath.evaluate(
                                resource,
                                this.elements[index].fhirpath,
                                null,
                                fhirpath_r4_model
                            );
                        } catch (e) {
                            if (e.message.includes("TypeExpression")) {
                                this.elements[index].value = [
                                    "the fhirpath could not be evaluated by the library",
                                ];
                            } else {
                                throw e;
                            }
                        }
                    };
                    return JSON.parse(JSON.stringify(this))
                });
            }
    """,
        args=[resources],
        g=elements,
    )
    return result
