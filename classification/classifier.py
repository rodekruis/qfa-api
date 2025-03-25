from classification.schema import ClassificationSchema
from classification.result import ClassificationResult
from transformers import pipeline
import os

zeroshot_classifier = pipeline(
    "zero-shot-classification", model=os.getenv("ZEROSHOT_CLASSIFIER")
)


class Classifier:
    """
    Classifier base class
    """

    def __init__(self, model: str, cs: ClassificationSchema):
        self.model = model
        self.cs = cs

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify text
        """
        hypothesis_template = "This text is about {}"
        labels_1 = self.cs.get_labels(level=1)
        output = zeroshot_classifier(
            text,
            labels_1,
            hypothesis_template=hypothesis_template,
            multi_label=False,
        )
        label_1 = output["labels"][output["scores"].index(max(output["scores"]))]
        label_2, label_3 = None, None
        if self.cs.n_levels > 1:
            labels_2 = self.cs.get_labels(
                level=2, parent=self.cs.get_id_from_label(label_1)
            )
            if len(labels_2) == 1:
                label_2 = labels_2[0]
            elif len(labels_2) > 1:
                output = zeroshot_classifier(
                    text,
                    labels_2,
                    hypothesis_template=hypothesis_template,
                    multi_label=False,
                )
                label_2 = output["labels"][
                    output["scores"].index(max(output["scores"]))
                ]
        if self.cs.n_levels > 2:
            if label_2:
                labels_3 = self.cs.get_labels(
                    level=3, parent=self.cs.get_id_from_label(label_2)
                )
                if len(labels_3) == 1:
                    label_3 = labels_3[0]
                elif len(labels_3) > 1:
                    output = zeroshot_classifier(
                        text,
                        labels_3,
                        hypothesis_template=hypothesis_template,
                        multi_label=False,
                    )
                    label_3 = output["labels"][
                        output["scores"].index(max(output["scores"]))
                    ]

        return ClassificationResult(
            text=text,
            result_level1={
                "label": label_1,
                "id": self.cs.get_id_from_label(label_1),
            },
            result_level2={
                "label": label_2,
                "id": self.cs.get_id_from_label(label_2),
            },
            result_level3={
                "label": label_3,
                "id": self.cs.get_id_from_label(label_3),
            },
            source_settings=self.cs.settings,
        )
