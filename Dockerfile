FROM python:3.12-alpine
WORKDIR /app
COPY manager.py /app/manager.py
EXPOSE 3000
CMD ["python", "-u", "/app/manager.py"]
