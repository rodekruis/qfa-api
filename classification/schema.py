from typing import List
from fastapi import HTTPException
from utils.logger import logger
from utils.espocrm import EspoAPI, EspoFormatLink
from utils.sources import Source
from utils.translate import translate_text
from utils.cosmos import cosmos_container_client, cosmos_source_id
from azure.cosmos.exceptions import CosmosResourceExistsError
import requests


class ClassificationSchemaRecord:
    """
    Classification schema record base class
    """

    def __init__(
        self,
        id: str,
        label: str,
        level: int,
        parent: str = None,
        examples: List[str] = None,
        label_en: str = None,
        has_examples: bool = False,
    ):
        self.id = id  # unique ID of the record: Kobo choice name or EspoCRM record id
        self.label = label  # class label
        self.label_en = (
            label_en if label_en else label
        )  # class label translated to English
        self.level = level  # level of the record in the classification schema
        self.parent = parent  # parent record ID if the record is not at the top level
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
    Classification schema base class
    """

    def __init__(self, source_settings: dict = None):
        self.settings = source_settings  # source settings
        self.source = Source(source_settings["source-name"].lower())  # source name
        self.data = []  # classification schema records
        self.n_levels = len(
            set([record.level for record in self.data])
        )  # number of levels in the schema
        self.version_id = ""  # version ID of the schema

    def get_class_id(self, label_en: str) -> str | None:
        """
        Get class id from label_en
        """
        if not label_en:
            return None
        for record in self.data:
            if record.label_en == label_en:
                return record.id
        raise ValueError(f"Label {label_en} not found in classification schema")

    def get_class_label(self, label_en: str) -> str | None:
        """
        Get class label from label_en
        """
        if not label_en:
            return None
        for record in self.data:
            if record.label_en == label_en:
                return record.label
        raise ValueError(f"Label {label_en} not found in classification schema")

    def get_labels(self, level: int, parent: str = None) -> List[str]:
        """
        Get class labels in English for a given level and parent name
        """
        labels = []
        for record in self.data:
            if parent is None:
                if record.level == level:
                    labels.append(record.label_en)
            else:
                if record.level == level and record.parent == parent:
                    labels.append(record.label_en)
        return labels

    def is_up_to_date(self) -> bool:
        """
        Check if classification schema is up-to-date by comparing version_id between source and CosmosDB.
        """
        is_version_id_up_to_date = True
        if self.source == Source.KOBO:
            headers = {
                "Authorization": f"Token {self.settings['source-authorization']}"
            }
            URL = f"https://kobo.ifrc.org/api/v2/assets/{self.settings['source-origin']}/?format=json"
            form = requests.get(URL, headers=headers).json()
            if "content" not in form.keys():
                raise HTTPException(
                    status_code=404,
                    detail=f"Kobo form {self.settings['source-origin']} not found or unauthorized",
                )
            is_version_id_up_to_date = self.version_id == form["deployed_version_id"]
        elif self.source == Source.ESPOCRM:
            client = EspoAPI(
                self.settings["source-origin"], self.settings["source-authorization"]
            )
            params = {
                "select": "modifiedAt",
                "maxSize": 1,
                "orderBy": "modifiedAt",
                "order": "desc",
            }
            # use as version id the latest modifiedAt
            modifiedAts = []
            for lvl in range(1, self.n_levels + 1):
                modifiedAts.append(
                    client.request("GET", self.settings[f"source-level{lvl}"], params)[
                        "content"
                    ]["list"][0]["modifiedAt"]
                )
            is_version_id_up_to_date = self.version_id == max(modifiedAts)
        return is_version_id_up_to_date

    def load_from_source(self):
        """
        Load classification schema from source
        """
        cs_records = []
        translate = self.settings.get("translate", False)
        if self.source == Source.ESPOCRM:
            logger.info("Loading classification schema from EspocRM.")
            client = EspoAPI(
                self.settings["source-origin"], self.settings["source-authorization"]
            )
            list1 = client.request("GET", self.settings["source-level1"])["content"][
                "list"
            ]
            list2, list3 = [], []
            logger.info(f"Level 1 records: {list1}")
            for level1_record in list1:
                cs_records.append(
                    ClassificationSchemaRecord(
                        id=level1_record["id"],
                        label=level1_record["name"],
                        label_en=(
                            translate_text(level1_record["name"]) if translate else None
                        ),
                        level=1,
                    )
                )
            if self.settings["source-level2"]:
                level1_link = EspoFormatLink(self.settings["source-level1"], "Id")
                list2 = client.request("GET", self.settings["source-level2"])[
                    "content"
                ]["list"]
                for level2_record in list2:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            id=level2_record["id"],
                            label=level2_record["name"],
                            label_en=(
                                translate_text(level2_record["name"])
                                if translate
                                else None
                            ),
                            level=2,
                            parent=level2_record[level1_link],
                        )
                    )
            if self.settings["source-level3"]:
                level2_link = EspoFormatLink(self.settings["source-level2"], "Id")
                list3 = client.request("GET", self.settings["source-level3"])[
                    "content"
                ]["list"]
                for level3_record in list3:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            id=level3_record["id"],
                            label=level3_record["name"],
                            label_en=(
                                translate_text(level3_record["name"])
                                if translate
                                else None
                            ),
                            level=3,
                            parent=level3_record[level2_link],
                        )
                    )
            self.version_id = max(
                [level1["modifiedAt"] for level1 in list1]
                + [level2["modifiedAt"] for level2 in list2]
                + [level3["modifiedAt"] for level3 in list3]
            )  # use as version id the latest modifiedAt

        elif self.source == Source.KOBO:
            logger.info("Loading classification schema from Kobo.")
            headers = {
                "Authorization": f"Token {self.settings['source-authorization']}"
            }
            URL = f"https://kobo.ifrc.org/api/v2/assets/{self.settings['source-origin']}/?format=json"
            form = requests.get(URL, headers=headers).json()
            if "content" not in form.keys():
                raise HTTPException(
                    status_code=404,
                    detail=f"Kobo form {self.settings['source-origin']} not found or unauthorized",
                )
            self.version_id = form["deployed_version_id"]
            form = form["content"]

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
                            id=choice["name"],
                            label=choice["label"][0],
                            label_en=(
                                translate_text(choice["label"][0])
                                if translate
                                else None
                            ),
                            level=1,
                        )
                    )
                if list2 and choice["list_name"] == list2 and conditional_column2:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            id=choice["name"],
                            label=choice["label"][0],
                            label_en=(
                                translate_text(choice["label"][0])
                                if translate
                                else None
                            ),
                            level=2,
                            parent=choice[conditional_column2],
                        )
                    )
                if list3 and choice["list_name"] == list3 and conditional_column3:
                    cs_records.append(
                        ClassificationSchemaRecord(
                            id=choice["name"],
                            label=choice["label"][0],
                            label_en=(
                                translate_text(choice["label"][0])
                                if translate
                                else None
                            ),
                            level=3,
                            parent=choice[conditional_column3],
                        )
                    )
        else:
            raise NotImplementedError(
                f"Classification schema source {self.source.value} is not supported"
            )
        self.n_levels = len(set([record.level for record in cs_records]))
        self.data = cs_records

    def save_to_cosmos(self):
        """
        Save classification schema to CosmosDB
        """
        schema = {
            "id": cosmos_source_id(self.source, self.settings["source-origin"]),
            "source": self.source.value,
            "n_levels": self.n_levels,
            "data": [vars(record) for record in self.data],
            "version_id": self.version_id,
        }
        try:
            cosmos_container_client.create_item(body=schema)
        except CosmosResourceExistsError:
            cosmos_container_client.replace_item(item=str(schema["id"]), body=schema)

    def load_from_cosmos(self):
        """
        Load classification schema from CosmosDB
        """
        source_id = cosmos_source_id(self.source, self.settings["source-origin"])
        schema = cosmos_container_client.read_item(
            item=source_id, partition_key=self.source.value
        )
        self.source = Source(schema["source"])
        self.n_levels = schema["n_levels"]
        self.data = [ClassificationSchemaRecord(**record) for record in schema["data"]]
        self.version_id = schema["version_id"]

    def remove_from_cosmos(self):
        """
        Remove classification schema from CosmosDB
        """
        source_id = cosmos_source_id(self.source, self.settings["source-origin"])
        try:
            cosmos_container_client.delete_item(body=source_id)
        except CosmosResourceExistsError:
            logger.info(f"Classification schema {source_id} not found in CosmosDB.")
