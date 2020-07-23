"""set of functions allowing to use the javascript coded library on the repository https://github.com/HL7/fhirpath.js
"""  # noqa
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
            )
    } catch (e) {
        %(result_keyword)s +
        console.log(JSON.stringify({error: e.message}) +
        %(result_keyword)s);
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
    prc = Popen(
        "node",
        shell=False,
        stderr=PIPE,
        stdout=PIPE,
        stdin=PIPE,
        cwd="fhir2dataset/metadata",
        encoding="utf-8",
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
def multiple_search_dict(resources, fhirpaths):
    """constructs a list composed of the elements resulting from the fhirpaths contained in the 'fhirpaths' argument applied to an instance of a resource and then concatenates all these lists into a larger list for all resources contained in the 'resources' argument.

    Args:
        resources (list): json, corresponding to a fhir resource, list 
        fhirpaths (list): list of fhirpaths to be applied to each resource

    Returns:
        list: the element list[1][2] corresponds to the element found by the fhirpath at position 1 in the 'fhirpaths' list on the instance at position 2 in the 'resources' list
    """  # noqa
    result = execute(
        """function test(resources, fhirpaths) {
                const fhirpath = require("fhirpath");
                const fhirpath_r4_model = require("fhirpath/fhir-context/r4");

                return resources.map((resource) => {
                    return fhirpaths.map((fhirpath_exp) => {
                        try {
                            return fhirpath.evaluate(
                                resource,
                                fhirpath_exp,
                                null,
                                fhirpath_r4_model
                            );
                        } catch (e) {
                            if (e.message.includes("TypeExpression")) {
                                return [
                                    "the fhirpath could not be evaluated by the library",
                                ];
                            } else {
                                throw e;
                            }
                        }
                    });
                });
            }
    """,
        args=[resources, fhirpaths],
    )
    return result
