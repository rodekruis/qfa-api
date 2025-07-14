from typing import List
from classification.schema import ClassificationSchema
from classification.result import ClassificationResult
from utils.translate import translate_text
from transformers import pipeline
from openai import AzureOpenAI
from fuzzywuzzy import process
import os

# initialize classifier client
if os.getenv("CLASSIFIER_PROVIDER") == "HuggingFace":
    hf_classifier = pipeline(
        "zero-shot-classification", model=os.getenv("CLASSIFIER_MODEL")
    )
elif os.getenv("CLASSIFIER_PROVIDER") == "OpenAI":
    client = AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )


def classify_text(text: str, classes: List[str]) -> str:
    """
    Classify text using the classification model.

    Args:
        text (str): The text to classify.
        classes (list): List of classes to classify against.

    Returns:
        str: Predicted class.
    """
    # if only one class is provided, just return it
    if len(classes) == 1:
        return classes[0]

    predicted_class = ""
    if os.getenv("CLASSIFIER_PROVIDER") == "HuggingFace":
        prompt = "This text is about {}"
        output = hf_classifier(
            text,
            classes,
            hypothesis_template=prompt,
            multi_label=False,
        )
        predicted_class = output["labels"][
            output["scores"].index(max(output["scores"]))
        ]
    elif os.getenv("CLASSIFIER_PROVIDER") == "OpenAI":
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that helps humanitarian workers classify messages received "
                    f"by beneficiaries. Your task is to classify the message into one of the following categories: {classes}. "
                    "Respond with the category name only. Your response must correspond to one of the categories.",
                },
                {
                    "role": "user",
                    "content": f"I suggest you contact the communities first before distributing aid.",
                },
            ],
            max_completion_tokens=50,
            temperature=0.2,
            top_p=0.1,
            model=os.getenv("CLASSIFIER_MODEL"),
        )
        predicted_class = response.choices[0].message.content.strip()
        # fuzzy-match the closest class, to ensure the predicted class is one of the input classes
        predicted_class = process.extractOne(predicted_class, classes)[0]
    return predicted_class


class Classifier:
    """
    Classifier base class
    """

    def __init__(self, schema: ClassificationSchema, translate: bool = False):
        self.schema = schema
        self.translate = translate

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify text based on classification schema
        """

        labels_1 = self.schema.get_labels_en(level=1)
        if self.translate:
            text = translate_text(text)
        label_1 = classify_text(text, labels_1)
        label_2, label_3 = None, None
        if self.schema.n_levels > 1:
            labels_2 = self.schema.get_labels_en(
                level=2, parent=self.schema.get_class_id(label_1)
            )
            label_2 = classify_text(text, labels_2)
        if self.schema.n_levels > 2:
            if label_2:
                labels_3 = self.schema.get_labels_en(
                    level=3, parent=self.schema.get_class_id(label_2)
                )
                label_3 = classify_text(text, labels_3)

        return ClassificationResult(
            text=text,
            result_level1={
                "label": self.schema.get_class_label(label_en=label_1),
                "id": self.schema.get_class_id(label_en=label_1),
            },
            result_level2={
                "label": self.schema.get_class_label(label_en=label_2),
                "id": self.schema.get_class_id(label_en=label_2),
            },
            result_level3={
                "label": self.schema.get_class_label(label_en=label_3),
                "id": self.schema.get_class_id(label_en=label_3),
            },
            source_settings=self.schema.settings,
        )
