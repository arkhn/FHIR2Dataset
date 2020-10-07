const Graph = require('digraphe')
const fhirpath_module = require("fhirpath");
const fhirpath_r4_model = require("fhirpath/fhir-context/r4");

const create_graph = (nodes_dict_raw, edges_array_raw) => {
    let graph = new Graph();

    for (const [key, value] of Object.entries(nodes_dict_raw)) {
        graph.addNode(key, { fhirpath: value["fhirpath"], parsed_fhirpath: value["parsed_fhirpath"], column_idx: value["column_idx"] })
    }

    edges_array_raw.forEach(edge => {
        graph.addEdge(
            edge[0],
            edge[1]
        );
    });
    return graph
}


const dfs = (graph, root_id, input, fhirpath_number) => {
    let result = []
    try {
        let output = fhirpath_module.applyParsedPath(
            input,
            JSON.parse(JSON.parse(graph.nodes[root_id].object.parsed_fhirpath)),
            null,
            fhirpath_r4_model
        );
        if (graph.nodes[root_id].adjacents().length !== 0) {
            output.forEach((tmp_input) => {

                let res = graph.nodes[root_id].adjacents().map((element) => {
                    if (element.object.column_idx.includes(fhirpath_number)) {
                        return dfs(graph, element.id, tmp_input, fhirpath_number)
                    }
                })
                result = result.concat(res.filter(Boolean))
            })

        } else {
            result = output.length === 0 ? [null] : output
        }
        return result
    } catch (e) {
        if (e.message.includes("TypeExpression")) {
            return [
                "the fhirpath could not be evaluated by the library",
            ];
        } else {
            throw e;
        }
    }

}

const compute_fhirpaths = (nodes_dict_raw, edges_array_raw, root_id, resource, result) => {
    if (typeof result === 'undefined') {
        result = []
    }

    const graph = create_graph(nodes_dict_raw, edges_array_raw)
    columns_idx = graph.nodes[root_id].object.column_idx
    console.log('columns_idx', columns_idx)
    columns_idx.forEach(element => {
        result[element] = dfs(graph, root_id, resource, element)
    });
    return result
}

module.exports = {
    compute_fhirpaths: compute_fhirpaths
}
