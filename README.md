# qfa-api

Qualitative Feedback Analysis (QFA) API.

## Description

Synopsis: a [dockerized](https://www.docker.com/) [python](https://www.python.org/) API to analyze qualitative feedback.

Powered by [open-source language models](https://huggingface.co/). Uses [Poetry](https://python-poetry.org/) for dependency management.

## Setup classification with Kobo

1. Prepare a kobo form as follows:
   * add one question of type `text`, whose content will be classified. Example: `feedback`.
   * add up to three cascading select questions of type `select_one`, which determine how the text will be classified. Example: `type`, `category`, `code`.
   * fill in the possible choices in the `choices` sheet of the form exactly as explained [here](https://support.kobotoolbox.org/cascading_select.html#adding-cascading-question-sets-in-xlsform-option-1).
   * upload and deploy the form.

> [!TIP]
> The text will be classified according to the `labels` of the choices. A few tips to improve the accuracy of the classification:
> * The model can**not** possibly know all humanitarian acronyms, so make sure to spell them out. Example: use `Water, Sanitation and Hygiene` instead of `WASH`, or `Red Crescent` instead of `RC`.
> * Avoid using ambiguous labels and be specific. Example: use `distribution of non-food items` and `distribution of cash` instead of `relief` and `cash`.
> * The more choices you provide, the less accurate the classification will be. Keep the number of choices below 10 in each cascading select question.

2. [Register a new Kobo REST Service](https://support.kobotoolbox.org/rest_services.html) and configure it as follows:
   * insert as `Endpoint URL`
    ```
    https://qfa-api.azurewebsites.net/classify-text
    ```
   * add the following headers under `Custom HTTP Headers`:
       * under `Name` insert `text-field` and under `Value` the name of the text question to be classified. Example: `feedback`.
       * under `Name` insert `source-name` and under `Value` just `kobo`.
       * under `Name` insert `source-origin` and under `Value` the ID of the form (see [where to find it](https://im.unhcr.org/kobosupport/)).
       * under `Name` insert `source-authorization` and under `Value` your Kobo token (see [how to get one](https://support.kobotoolbox.org/api.html#getting-your-api-token)).
       * under `Name` insert `source-level1` and under `Value` the name of the first of the cascading select questions. Example: `type`.
       * under `Name` insert `source-level2` and under `Value` the name of the second of the cascading select questions. Example: `category`.
       * under `Name` insert `source-level3` and under `Value` the name of the third of the cascading select questions. Example: `code`.

_That's it_. Your submissions will be automatically classified in a few seconds. Happy qualitative feedback analysis!


![img.png](img.png)


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

### Run with Docker

```sh
docker compose up --detach
```

