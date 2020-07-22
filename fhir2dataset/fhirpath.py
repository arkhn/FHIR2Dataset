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
        var result = (%(func)s).apply(globals, %(args)s);
        if ((typeof result) == 'string') {
            result = JSON.stringify(result);
        }
        console.log(JSON.stringify({"result": result}))
    } catch (e) {
        console.log(JSON.stringify({error: e.message}));
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
    prc = Popen(
        "node",
        shell=False,
        stderr=PIPE,
        stdout=PIPE,
        stdin=PIPE,
        cwd="fhir2dataset/metadata",
        encoding="utf-8",
    )

    c = wrapper % {"func": code, "globals": json.dumps(g), "args": json.dumps(args)}
    outs, errs = prc.communicate(input=c)
    if isinstance(outs, str):
        try:
            outs = json.loads(outs)
        except:
            logger.warning(f"outs: {outs}")
            logger.warning(f"errs: {errs}")
            raise
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
                            const result = fhirpath.evaluate(
                                resource,
                                fhirpath_exp,
                                null,
                                fhirpath_r4_model
                            );
                            return result;
                        } catch (e) {
                            if (e.message.includes("TypeExpression")) {
                                const result = [
                                    "the fhirpath could not be evaluated by the library",
                                ];
                                return result;
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
