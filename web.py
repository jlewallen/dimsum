import quart

app = quart.Quart(__name__)


@app.route("/")
def main_index():
    return {"version": 1.0}
