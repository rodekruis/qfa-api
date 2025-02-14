import requests

import requests

response = requests.post(
    # f'https://hia-chatbot.azurewebsites.net/ask',
    "http://127.0.0.1:8000/classify-text",
    json={
        "_id": "7401881",
        "feedback": "I request information on the Red Cross cash programme",
    },
    headers={
        "source-name": "kobo",
        "source-origin": "asroL6e9wJLh62GNSJ7cHR",
        "source-authorization": "4eca639d4031e8355f70d87a19b2382afb12f17b",
        "source-level1": "Feedback_Type",
        "source-level2": "Feedback_Category",
        "source-level3": "Feedback_Code",
        "text-field": "feedback",
    },
)
print(response, response.content)

# {
#   "source_name": "kobo",
#   "source_origin": "asroL6e9wJLh62GNSJ7cHR",
#   "source_authorization": "4eca639d4031e8355f70d87a19b2382afb12f17b",
#   "source_level1": "Feedback_Type",
#   "source_level2": "Feedback_Category",
#   "source_level3": "Feedback_Code"
# }
