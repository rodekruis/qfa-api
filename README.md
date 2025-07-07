# qfa-api

Qualitative Feedback Analysis (QFA) API.

## Description

Synopsis: a [dockerized](https://www.docker.com/) [python](https://www.python.org/) API to analyze qualitative feedback.

Powered by [open-source language models](https://huggingface.co/). Uses [Poetry](https://python-poetry.org/) for dependency management.

## Setup classification with Kobo

1. Prepare a kobo form as follows:
   * add one question of type `text`, whose content will be classified. Example: `feedback`.
   * add up to three cascading select questions of type `select_one` which will determine how the text will be classified. Example: `type`, `category`, `code`.
   * fill in the possible choices in the `choices` sheet of the form exactly as explained [here](https://support.kobotoolbox.org/cascading_select.html#adding-cascading-question-sets-in-xlsform-option-1); these choices will be used as labels for the classification.
   * upload and deploy the form.

> [!TIP]
> The text will be classified according to the `labels` of the choices. A few tips to improve the accuracy of the classification:
>  * Phrase the label as if explaining to a 10-year-old. This helps the classification model grasp the core idea without unnecessary complexity.
>  * The model can**not** possibly know all humanitarian acronyms, so make sure to spell them out. Example: use `Water, Sanitation and Hygiene` instead of `WASH`, or `Red Crescent` instead of `RC`.
> * Avoid using ambiguous labels and be specific. Example: use `distribution of non-food items` and `distribution of cash` instead of `relief` and `cash`.
> * The more choices you provide, the less accurate the classification will be. Keep the number of choices as low as possible.
> * Try to use three synonyms when defining a label, for extra clarity. Example: use `misinformation, fake news and made-up stories` instead of only `misinformation`.

2. [Register a new Kobo REST Service](https://support.kobotoolbox.org/rest_services.html) and configure it as follows:
   * insert as `Endpoint URL`
    ```
    https://qfa-api.azurewebsites.net/classify-text
    ```
   * add the following headers under `Custom HTTP Headers`:
       * under `Name` insert `API-KEY` and under `Value` insert the QFA API key (see Bitwarden).
       * under `Name` insert `source-text` and under `Value` insert the name of the text question to be classified. Example: `feedback`.
       * under `Name` insert `source-name` and under `Value` insert `kobo`.
       * under `Name` insert `source-origin` and under `Value` insert the ID of the form (see [where to find it](https://im.unhcr.org/kobosupport/)).
       * under `Name` insert `source-authorization` and under `Value` insert your Kobo token (see [how to get one](https://support.kobotoolbox.org/api.html#getting-your-api-token)).
       * under `Name` insert `source-level1` and under `Value` insert the name of the first of the cascading select questions. Example: `type`.
       * under `Name` insert `source-level2` and under `Value` insert the name of the second of the cascading select questions. Example: `category`.
       * under `Name` insert `source-level3` and under `Value` insert the name of the third of the cascading select questions. Example: `code`.
       * [OPTIONAL] under `Name` insert `translate` and under `Value` insert `true`, if you are using a language other than English; this will translate the text to English before classifying it (the results will still be in the original language, as specified in the classification schema).

_That's it_. Your submissions will be automatically classified in a few seconds. Happy qualitative feedback analysis!


<img width="763" alt="image" src="https://github.com/user-attachments/assets/919ebe53-17f4-4c5a-8937-baeae32dc4ff" />


### Current limitations using QFA with Kobo forms
1. It is not possible to use [repeating groups](https://support.kobotoolbox.org/group_repeat.html) in Kobo forms and repeatedly submit the classification request to QFA. If it is needed to copy/paste data from a previous form into another multiple forms, one could look at how to use [dynamic data attachments](https://support.kobotoolbox.org/dynamic_data_attachment.html) instead. 
2. It is not possible to edit an already submitted Kobo form and then re-submit with the goal of classifying again. Kobo does not allow the REST service to be triggered twice for the same submission.

## Setup classification with EspoCRM

Prerequisite: EspoCRM with [Advanced Pack](https://www.espocrm.com/extensions/advanced-pack/) installed.

1. Prepare EspoCRM as follows:
   * Create or select one entity which will be classified, e.g. `Feedback`.
   * Create or select one field of type `Text`, whose content will be classified, e.g. `feedbackText`. Tip: enable `Audited` so that changes can be traced.
   * Create or select up to three entities which will determine how the text will be classified, e.g. `Type`, `Category`, `Code`. The records' names will be used as labels for the classification.
   * Link these three entities to the entity that will be classified, by creating a relationship of type `Many-to-One` for each of them.
   * Create a new role with `Read` permissions over `Type`, `Category`, `Code`, and assign this role to a new API user.
2. Classification can then be performed automatically via Flowchart, using a Task with two Actions: 
   * `Send HTTP Request` to the QFA API
```
Request Type
POST

URL
https://qfa-api.azurewebsites.net/classify-text

Headers
API-KEY: <QFA API key>
source-name: espocrm
source-origin: <your EspoCRM instance URL>
source-authorization: <your EspoCRM API key>
source-level1: Type
source-level2: Category
source-level3: Code

Payload
{
    "text": "{$feedbackText}",
}
```

   * `Execute Formula Script` to save results to 
```
typeId = json\retrieve($_lastHttpResponseBody, 'TypeId');
categoryId = json\retrieve($_lastHttpResponseBody, 'CategoryId');
codeId = json\retrieve($_lastHttpResponseBody, 'CodeId');
```




## API Usage

See [the docs](https://qfa-api.azurewebsites.net/docs).

## Configuration

```sh
cp example.env .env
```

and edit the provided [ENV-variables](./example.env) accordingly.

### Run locally

```sh
pip install poetry
poetry install --no-root
uvicorn main:app --reload
```

