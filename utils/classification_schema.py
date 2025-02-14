from typing import List
from fastapi import HTTPException
from utils.logger import logger
from clients.espo_api_client import EspoAPI
import requests
import pandas as pd
from utils.cosmos import cosmos_container_client
from azure.cosmos.exceptions import CosmosResourceExistsError


def formatEntityAsLinkName(entity: str) -> str:
    """
    Format Entity name to the default EspoCRML link name
    """
    # lowercase first letter
    entity = entity[0].lower() + entity[1:]
    # add Id at the end
    entity = entity + "Name"
    return entity


class ClassificationSchemaRecord:

    def __init__(
        self,
        name: str,
        label: str,
        level: int,
        parent: str = None,
        examples: List[str] = None,
        has_examples: bool = False,
    ):
        self.name = name
        self.label = label
        self.level = level
        self.parent = parent
        if self.level > 1:
            assert self.parent, "Parent is required for records with level above 1"
        self.examples = examples
        if examples:
            assert isinstance(examples, list), "Examples must be a list"
            self.has_examples = True
            assert self.has_examples == has_examples, "has_examples should be True"
        else:
            self.has_examples = False
            assert self.has_examples == has_examples, "has_examples should be False"


class ClassificationSchema:
    """
    ClassificationSchema
    """

    def __init__(self, source: str, source_settings: dict = None):
        self.source = source
        self.settings = source_settings
        self.data = []
        self.n_levels = len(set([record.level for record in self.data]))

    def get_name_from_label(self, label: str) -> str | None:
        """
        Get class name from label
        """
        if not label:
            return None
        for record in self.data:
            if record.label == label:
                return record.name
        raise ValueError(f"Label {label} not found in classification schema")

    def get_class_labels(self, level: int, parent: str = None) -> List[str]:
        """
        Get class labels for a given level and parent name
        """
        labels = []
        for record in self.data:
            if parent is None:
                if record.level == level:
                    labels.append(record.label)
            else:
                if record.level == level and record.parent == parent:
                    labels.append(record.label)
        return labels

    def load_from_source(self):
        """
        TBI
        """
        cs_records = []
        if self.source.lower() == "espocrm":
            # check metadata TBI

            logger.info("Loading classification schema from EspocRM.")
            client = EspoAPI(
                self.settings["source-origin"], self.settings["source-authorization"]
            )
            level1_records = client.request("GET", self.settings["source-level1"])
            for level1_record in level1_records["list"]:
                cs_records.append(
                    ClassificationSchemaRecord(name=level1_record["name"], level=1)
                )
            if self.settings["source-level2"]:
                level1_link = formatEntityAsLinkName(self.settings["source-level1"])
                level2_records = client.request("GET", self.settings["source-level2"])
                for level2_record in level2_records["list"]:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=level2_record["name"],
                            level=2,
                            parent=level2_record[level1_link],
                        )
                    )
            if self.settings["source-level3"]:
                level2_link = formatEntityAsLinkName(self.settings["source-level2"])
                level3_records = client.request("GET", self.settings["source-level3"])
                for level3_record in level3_records["list"]:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=level3_record["name"],
                            level=3,
                            parent=level3_record[level2_link],
                        )
                    )

        elif self.source.lower() == "kobo":
            # check metadata TBI
            logger.info("Loading classification schema from Kobo.")
            headers = {
                "Authorization": f"Token {self.settings['source-authorization']}"
            }
            URL = f"https://kobo.ifrc.org/api/v2/assets/{self.settings['source-origin']}/files"
            file_url = requests.get(URL, headers=headers).json()["results"][0][
                "content"
            ]
            file = requests.get(file_url, headers=headers, allow_redirects=True)
            open("schema.csv", "wb").write(file.content)
            try:
                df_schema = pd.read_csv("schema.csv")
            except pd.errors.ParserError:
                try:
                    df_schema = pd.read_csv("schema.csv", delimiter=";")
                except pd.errors.ParserError:
                    raise HTTPException(
                        status_code=400,
                        detail="Could not parse the schema file. Please check the file format.",
                    )
            df_schema_lvl1 = df_schema.dropna(
                subset=[self.settings["source-level1"] + "_name"]
            ).drop_duplicates(subset=[self.settings["source-level1"] + "_name"])
            for ix, level1_record in df_schema_lvl1.iterrows():
                cs_records.append(
                    ClassificationSchemaRecord(
                        name=level1_record[self.settings["source-level1"] + "_name"],
                        label=level1_record[self.settings["source-level1"] + "_label"],
                        level=1,
                    )
                )
            if self.settings["source-level2"]:
                df_schema_lvl2 = df_schema.dropna(
                    subset=[
                        self.settings["source-level1"] + "_name",
                        self.settings["source-level2"] + "_name",
                    ]
                ).drop_duplicates(
                    subset=[
                        self.settings["source-level1"] + "_name",
                        self.settings["source-level2"] + "_name",
                    ]
                )
                for ix, level2_record in df_schema_lvl2.iterrows():
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=level2_record[
                                self.settings["source-level2"] + "_name"
                            ],
                            label=level2_record[
                                self.settings["source-level2"] + "_label"
                            ],
                            level=2,
                            parent=level2_record[
                                self.settings["source-level1"] + "_name"
                            ],
                        )
                    )
            if self.settings["source-level3"]:
                df_schema_lvl3 = df_schema.dropna(
                    subset=[
                        self.settings["source-level1"] + "_name",
                        self.settings["source-level2"] + "_name",
                        self.settings["source-level3"] + "_name",
                    ]
                ).drop_duplicates(
                    subset=[
                        self.settings["source-level1"] + "_name",
                        self.settings["source-level2"] + "_name",
                        self.settings["source-level3"] + "_name",
                    ]
                )
                for ix, level3_record in df_schema_lvl3.iterrows():
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=level3_record[
                                self.settings["source-level3"] + "_name"
                            ],
                            label=level3_record[
                                self.settings["source-level3"] + "_label"
                            ],
                            level=3,
                            parent=level3_record[
                                self.settings["source-level2"] + "_name"
                            ],
                        )
                    )
        else:
            raise NotImplementedError(
                f"Classification schema source {self.source} is not supported"
            )
        self.n_levels = len(set([record.level for record in cs_records]))
        self.data = cs_records

    def save_to_cosmos(self):
        """
        Save classification schema to CosmosDB
        """
        schema = {
            "id": self.settings["source-origin"],
            "source": self.source,
            "n_levels": self.n_levels,
            "data": [vars(record) for record in self.data],
        }
        try:
            cosmos_container_client.create_item(body=schema)
        except CosmosResourceExistsError:
            cosmos_container_client.replace_item(item=str(schema["id"]), body=schema)

    def load_from_cosmos(self):
        """
        Load classification schema from CosmosDB
        """
        schema = cosmos_container_client.read_item(
            item=self.settings["source-origin"],
            partition_key=self.source,
        )
        self.source = schema["source"]
        self.n_levels = schema["n_levels"]
        self.data = [ClassificationSchemaRecord(**record) for record in schema["data"]]
