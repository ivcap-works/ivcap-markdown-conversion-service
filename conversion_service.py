import io
import math
from markitdown import MarkItDown, StreamInfo
from pydantic import BaseModel, Field
from pydantic import BaseModel, ConfigDict

from ivcap_service import getLogger, Service, JobContext
from ivcap_ai_tool import start_tool_server, ToolOptions, ivcap_ai_tool, logging_init

logging_init()
logger = getLogger("app")

service = Service(
    name="Conversion to Markdown Service",
    contact={
        "name": "Max Ott",
        "email": "max.ott@data61.csiro.au",
    },
    license={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT",
    },
)

from typing import ClassVar, Optional

class Request(BaseModel):
    SCHEMA: ClassVar[str] = "urn:sd:schema.markdown-conversion.request.2"
    jschema: str = Field(SCHEMA, alias="$schema")
    document: str = Field(description="IVCAP URN of the file to parse")
    policy: Optional[str] = Field("urn:ivcap:policy:ivcap.base.artifact", description="policy for the created markdown artifact")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "$schema": "urn:sd:schema.markdown-conversion.request.1",
                "document": "urn:sd:file.1234567890",
            }
        }
    )

class Result(BaseModel):
    SCHEMA: ClassVar[str] = "urn:sd:schema.markdown-conversion.1"
    jschema: str = Field(SCHEMA, alias="$schema")
    id: str = Field(..., alias="$id")
    markdown_urn: str = Field(
        description="URN of the markdown version of the uploaded document."
    )
    policy: Optional[str] = Field(None, alias="$policy", description="Policy of the created markdown artifact.")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "$schema": "urn:sd:schema.markdown-conversion.1",
                "markdown_urn": "urn:sd:file.1234567890",
            }
        }
    )


@ivcap_ai_tool("/", opts=ToolOptions(tags=["Markdown Conversion"]))
def conversion_service(req: Request, ctxt: JobContext) -> Result:
    """Parse uploaded document into markdown.

    This service fetches a document as an artifact from from IVCAP storage,
    creates a copy in markdown format using `MarkItDown`,
    and uploads the result back to IVCAP storage.

    This function orchestrates the complete document parsing workflow:
    1. Check if there is already a cached conversation of the document
    2. Downloads the source document from IVCAP storage
    3. Converts the document using MarkItDown with plugin support
    4. Uploads the generated markdown back to IVCAP storage
    5. Returns the URI of the uploaded markdown file
    """

    # 1. Check for cached conversion
    ivcap = ctxt.ivcap
    cl = list(ivcap.list_aspects(entity=req.document, schema=Result.SCHEMA, limit=1))
    cached = cl[0] if cl else None
    if cached:
        logger.info(f"Using cached document: {cached.markdown_urn}")
        return Result(markdown_urn=cached.markdown_urn) # should be able to simply return "cached"

    # 2. Download the source document
    logger.info(f"Converting document: {req.document}")
    doc = ivcap.get_artifact(req.document)

    # 3. Convert the document to markdown
    converter = MarkItDown(enable_plugins=True)
    ds = doc.as_file()
    cres = converter.convert(ds, stream_info=StreamInfo(mimetype=doc.mime_type))
    if not cres:
        raise ValueError(f"Failed to convert document '{req.document}' to markdown.")
    md = cres.markdown

    # 4.Upload the generated markdown to IVCAP storage
    ms = io.BytesIO(md.encode("utf-8"))
    cart = ivcap.upload_artifact(
        name=f"{doc.name}.md",
        io_stream=ms,
        content_type="text/markdown",
        content_size=len(md),
        policy=req.policy,
    )
    logger.info(f"Uploaded markdown to {cart.urn}")

    # 5. Return the URI of the artifact containing the markdown conversion
    result = Result(id=req.document, markdown_urn=cart.urn, policy=req.policy)
    return result


if __name__ == "__main__":
    start_tool_server(service)
