from utils.classification_schema import ClassificationSchema
from utils.classification_result import ClassificationResult
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
        labels_1 = self.cs.get_class_labels(1)
        output = zeroshot_classifier(
            text,
            labels_1,
            hypothesis_template=hypothesis_template,
            multi_label=False,
        )
        label_1 = output["labels"][output["scores"].index(max(output["scores"]))]
        result_level1, result_level2, result_level3 = (
            self.cs.get_name_from_label(label_1),
            None,
            None,
        )
        if self.cs.n_levels > 1:
            labels_2 = self.cs.get_class_labels(2, parent=result_level1)
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
            else:
                label_2 = None
            result_level2 = self.cs.get_name_from_label(label_2)
        if self.cs.n_levels > 2:
            if result_level2:
                labels_3 = self.cs.get_class_labels(3, parent=result_level2)
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
                else:
                    label_3 = None
                result_level3 = self.cs.get_name_from_label(label_3)

        return ClassificationResult(
            text=text,
            result_level1=result_level1,
            result_level2=result_level2,
            result_level3=result_level3,
            source_settings=self.cs.settings,
        )
