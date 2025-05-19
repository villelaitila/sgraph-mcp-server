from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from sgraph_helper import SGraphHelper

mcp = FastMCP("SGraph")

sgh = SGraphHelper()


class SGraphLoadModel(BaseModel):
    path: str


@mcp.tool()
async def sgraph_load_model(sgraph_load_model: SGraphLoadModel):
    """Load a sgraph from a file and return the model id."""
    model_id = await sgh.load_sgraph(sgraph_load_model.path)
    return {"model_id": model_id}


class SGraphGetRootElement(BaseModel):
    model_id: str


@mcp.tool()
async def sgraph_get_root_element(sgraph_get_root_element: SGraphGetRootElement):
    """Get the root element from a model."""
    model = sgh.get_model(sgraph_get_root_element.model_id)
    if model is None:
        return {"error": "Model not loaded"}
    element_dict = sgh.element_to_dict(model.rootNode)
    return {"element": element_dict}


class SGraphGetElement(BaseModel):
    model_id: str
    element_path: str


@mcp.tool()
async def sgraph_get_element(sgraph_get_element: SGraphGetElement):
    """Get an element from a model."""
    model = sgh.get_model(sgraph_get_element.model_id)
    if model is None:
        return {"error": "Model not loaded"}
    root_element = model.rootNode
    element = root_element.findElement(sgraph_get_element.element_path)
    if element is None:
        return {"error": "Element not found"}
    element_dict = sgh.element_to_dict(element)
    return {"element": element_dict}


class SGraphGetElementIncomingAssociations(BaseModel):
    model_id: str
    element_path: str


@mcp.tool()
async def sgraph_get_element_incoming_associations(
    sgraph_get_element_incoming_associations: SGraphGetElementIncomingAssociations,
):
    """Get the incoming associations of single element. Does not include the associations of the children."""  # noqa: E501
    model = sgh.get_model(sgraph_get_element_incoming_associations.model_id)
    if model is None:
        return {"error": "Model not loaded"}
    element = model.findElementFromPath(sgraph_get_element_incoming_associations.element_path)
    if element is None:
        return {"error": "Element not found"}
    incoming_associations_dicts = [
        sgh.element_to_dict(association.fromElement) for association in element.incoming
    ]
    return {"incoming_associations": incoming_associations_dicts}


class SGraphGetElementOutgoingAssociations(BaseModel):
    model_id: str
    element_path: str


@mcp.tool()
async def sgraph_get_element_outgoing_associations(
    sgraph_get_element_outgoing_associations: SGraphGetElementOutgoingAssociations,
):
    """Get the outgoing associations of single element. Does not include the associations of the children."""  # noqa: E501
    model = sgh.get_model(sgraph_get_element_outgoing_associations.model_id)
    if model is None:
        return {"error": "Model not loaded"}
    element = model.findElementFromPath(sgraph_get_element_outgoing_associations.element_path)
    if element is None:
        return {"error": "Element not found"}
    outgoing_associations_dicts = [
        sgh.element_to_dict(association.toElement) for association in element.outgoing
    ]
    return {"outgoing_associations": outgoing_associations_dicts}


if __name__ == "__main__":
    mcp.run(transport="sse")
