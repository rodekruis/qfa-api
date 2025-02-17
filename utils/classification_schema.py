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
            URL = f"https://kobo.ifrc.org/api/v2/assets/{self.settings['source-origin']}/?format=json"
            form = requests.get(URL, headers=headers).json()["content"]
            # this method assumes that the form is structured in a way that
            # 1) classification questions are in order (from level 1 to 3, from top to bottom)
            # 2) choice_filter is used on level2 question as <level1>=${<source-level1>}
            # 3) choice_filter is used on level3 question as <level1>=${<source-level1>} and <level2>=${<source-level2>}
            # 4) <level1> and <level2> appear as extra columns in the choices sheet
            list1, list2, list3 = None, None, None
            conditional_column2, conditional_column3 = None, None
            for question in form["survey"]:
                if (
                    question["type"] == "select_one"
                    and question["name"] == self.settings["source-level1"]
                ):
                    list1 = question["select_from_list_name"]
                if (
                    "source-level2" in self.settings.keys()
                    and question["type"] == "select_one"
                    and question["name"] == self.settings["source-level2"]
                ):
                    list2 = question["select_from_list_name"]
                    conditional_column2 = (
                        question["choice_filter"]
                        .replace(f"=${{{self.settings['source-level1']}}}", "")
                        .strip()
                    )
                if (
                    "source-level3" in self.settings.keys()
                    and question["type"] == "select_one"
                    and question["name"] == self.settings["source-level3"]
                ):
                    list3 = question["select_from_list_name"]
                    conditional_column3 = (
                        question["choice_filter"]
                        .replace(f"=${{{self.settings['source-level2']}}}", "")
                        .replace(
                            f"{conditional_column2}=${{{self.settings['source-level1']}}} and ",
                            "",
                        )
                        .strip()
                    )

            for choice in form["choices"]:
                if choice["list_name"] == list1:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=choice["name"],
                            label=choice["label"][0],
                            level=1,
                        )
                    )
                if list2 and choice["list_name"] == list2 and conditional_column2:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=choice["name"],
                            label=choice["label"][0],
                            level=2,
                            parent=choice[conditional_column2],
                        )
                    )
                if list3 and choice["list_name"] == list3 and conditional_column3:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            name=choice["name"],
                            label=choice["label"][0],
                            level=3,
                            parent=choice[conditional_column3],
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
