from flask import Flask, render_template, request, send_file
app = Flask(__name__)

# @app.route("/")
# def hello():
#     return "<h1 style='color:blue'>Hello There!</h1>"



@app.route('/')
def upload_landing():

    return render_template('index.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0')