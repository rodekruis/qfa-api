from fastapi import HTTPException
import requests
from fastapi.responses import JSONResponse
import json


class ClassificationResult:
    """
    Classification result base class
    """

    def __init__(
        self,
        text: str,
        result_level1: str,
        result_level2: str = None,
        result_level3: str = None,
        source_settings: dict = None,
    ):
        self.text = text
        self.result_level1 = result_level1
        self.result_level2 = result_level2
        self.result_level3 = result_level3
        self.settings = source_settings

    def save_to_source(self, payload: dict):
        """
        Save classification result to source
        """
        source_status_code, source_response = 100, {}
        # save to source
        if self.settings["source-name"].lower() == "espocrm":
            # TBI
            pass
        elif self.settings["source-name"].lower() == "kobo":
            headers = {
                "Authorization": f"Token {self.settings['source-authorization']}"
            }
            kobo_payload = {
                "submission_ids": [str(payload["_id"])],
                "data": {
                    self.settings["source-level1"]: self.result_level1,
                    self.settings["source-level2"]: self.result_level2,
                    self.settings["source-level3"]: self.result_level3,
                },
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

        return JSONResponse(status_code=source_status_code, content=source_response)
