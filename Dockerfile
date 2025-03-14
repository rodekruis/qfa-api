# python base image in the container from Docker Hub
FROM python:3.12-slim

# copy files to the /app folder in the container
ADD routes /app/routes
ADD utils /app/utils
ADD classification /app/classification
COPY ./main.py /app/main.py
COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock

# set the working directory in the container to be /app
WORKDIR /app

# install required packages
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-root
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu


# expose the port that uvicorn will run the app on
ENV PORT=8000
EXPOSE 8000

# execute the command python main.py (in the WORKDIR) to start the app
CMD ["python", "main.py"]
