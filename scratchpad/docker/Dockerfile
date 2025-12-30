FROM public.ecr.aws/docker/library/python:3-alpine
ADD code /code
WORKDIR /code
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "scratchpad.py"]