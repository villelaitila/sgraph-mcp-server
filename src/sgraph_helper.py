import asyncio
from typing import Any

import nanoid
from sgraph import SElement, SGraph
from sgraph.loader.modelloader import ModelLoader


class SGraphHelper:
    _models: dict[str, SGraph] = {}

    def __init__(self):
        self.ml = ModelLoader()

    async def load_sgraph(self, path: str) -> str:
        model = await asyncio.to_thread(self.ml.load_model, path)
        model_id = nanoid.generate(size=24)
        self._models[model_id] = model
        return model_id

    def get_model(self, model_id: str) -> SGraph | None:
        return self._models.get(model_id)

    def element_to_dict(
        self,
        element: SElement,
        additional_fields: list[str] = [],
    ) -> dict[str, Any]:
        return {
            "name": element.name,
            "path": element.getPath(),
            "type": element.getType(),
            "child_paths": [child.getPath() for child in element.children],
            **{
                field: getattr(element, field)
                for field in additional_fields
                if hasattr(element, field)
            },
        }
