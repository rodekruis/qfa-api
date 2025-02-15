# qfa-api

Qualitative Feedback Analysis (QFA) API.

## Description

Synopsis: a [dockerized](https://www.docker.com/) [python](https://www.python.org/) API to analyze qualitative feedback.

Powered by [open-source language models](https://huggingface.co/). Uses [Poetry](https://python-poetry.org/) for dependency management.

## Setup with classification with Kobo

1. Prepare a kobo form as follows:
   * one text question of type `text`, which will be classified. Example: `feedback`.
   * up to three cascading select questions of type `select_one`. Example: `type`, `category`, `code`.
   * fill in the possible choices in the `choices` sheet of the form exactly as explained [here](https://support.kobotoolbox.org/cascading_select.html#adding-cascading-question-sets-in-xlsform-option-1).
   * upload and deploy the form.
3. [Register a new Kobo REST Service](https://support.kobotoolbox.org/rest_services.html) and configure it as follows:
   * insert as `Endpoint URL`
    ```
    https://qfa-api.azurewebsites.net/classify-text
    ```
   * add the following headers under `Custom HTTP Headers`:
       * under `Name` insert `text-field` and under `Value` the name of the text question in the form. Example: `feedback`.
       * under `Name` insert `source-name` and under `Value` just `kobo`.
       * under `Name` insert `source-origin` and under `Value` the id of the form (see [where to find it](https://im.unhcr.org/kobosupport/)).
       * under `Name` insert `source-authorization` and under `Value` your Kobo token (see [how to get one](https://support.kobotoolbox.org/api.html#getting-your-api-token)).
       * under `Name` insert `source-level1` and under `Value` the name of the first of the cascading select questions. Example: `type`.
       * under `Name` insert `source-level2` and under `Value` the name of the second of the cascading select questions. Example: `category`.
       * under `Name` insert `source-level3` and under `Value` the name of the third of the cascading select questions. Example: `code`.

_That's it_. Happy qualitative feedback analysis!

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

