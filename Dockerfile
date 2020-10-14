FROM nikolaik/python-nodejs:python3.8-nodejs12

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN cd web && npm install && npm run build
RUN mv web/dist static
CMD [ "python", "/app/dimsum.py" ]