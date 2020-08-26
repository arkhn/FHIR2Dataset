"""set of functions allowing to use the javascript coded library on the repository https://github.com/HL7/fhirpath.js
"""  # noqa
import os
import json
import logging
from subprocess import Popen, PIPE

from fhir2dataset.timer import timing

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


@timing
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
        "node", shell=False, stderr=PIPE, stdout=PIPE, stdin=PIPE, cwd=path, encoding="utf-8",
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
        raise Exception((outs.get("error"), errs,))
    else:
        raise Exception(errs)


@timing
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


@timing
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
