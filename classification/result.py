from fastapi import HTTPException
import requests
from utils.espocrm import EspoAPI, EspoFormatLink
from utils.sources import Source
from utils.logger import logger
from fastapi.responses import JSONResponse
import json


class ClassificationResult:
    """
    Classification result base class
    """

    def __init__(
        self,
        text: str,
        result_level1: dict,
        result_level2: dict = None,
        result_level3: dict = None,
        source_settings: dict = None,
    ):
        self.text = text
        self.result_level1 = result_level1
        self.result_level2 = result_level2
        self.result_level3 = result_level3
        self.settings = source_settings
        self.source = Source(source_settings["source-name"].lower())

    def results(self):
        """
        Return classification results as a dictionary
        """
        if self.source == Source.KOBO:
            # dictionary as {<question name>: <answer>}
            results = {
                self.settings["source-level1"]: self.result_level1["label"],
                self.settings["source-level2"]: self.result_level2["label"],
                self.settings["source-level3"]: self.result_level3["label"],
            }
        elif self.source == Source.ESPOCRM:
            # dictionary as {<link>Id: <record id>, <link>Name: <record name>}
            results = {
                EspoFormatLink(
                    self.settings["source-level1"], "Name"
                ): self.result_level1["label"],
                EspoFormatLink(
                    self.settings["source-level1"], "Id"
                ): self.result_level1["id"],
                EspoFormatLink(
                    self.settings["source-level2"], "Name"
                ): self.result_level2["label"],
                EspoFormatLink(
                    self.settings["source-level2"], "Id"
                ): self.result_level2["id"],
                EspoFormatLink(
                    self.settings["source-level3"], "Name"
                ): self.result_level3["label"],
                EspoFormatLink(
                    self.settings["source-level3"], "Id"
                ): self.result_level3["id"],
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"results for source '{self.source}' is not supported.",
            )
        return results

    def save_to_source(self, payload: dict):
        """
        Save classification result to source
        """
        # save to source
        if self.source == Source.KOBO:
            headers = {
                "Authorization": f"Token {self.settings['source-authorization']}"
            }
            logger.info(f"Saving classification results to Kobo: {self.results()}")
            kobo_payload = {
                "submission_ids": [str(payload["_id"])],
                "data": self.results(),
            }
            kobo_response = requests.patch(
                url=f"https://kobo.ifrc.org/api/v2/assets/{self.settings['source-origin']}/data/bulk/",
                data={"payload": json.dumps(kobo_payload)},
                params={"fomat": "json"},
                headers=headers,
            )
            kobo_response = kobo_response.json()
            if (
                "results" in kobo_response
                and len(kobo_response["results"]) > 0
                and "status_code" in kobo_response["results"][0]
            ):
                source_response = kobo_response["results"][0]
                source_status_code = source_response["status_code"]
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No Kobo submissions match the given submission IDs: {kobo_payload['submission_ids']}",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot save classification results to {self.source}.",
            )

        return JSONResponse(status_code=source_status_code, content=source_response)
