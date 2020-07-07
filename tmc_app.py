import os
import zipfile
from pathlib import Path
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

GMAPS_API_KEY = os.getenv("GMAPS_API_KEY")

from tmc_summarizer.summarize import write_summary_file

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = Path("flask_user_data")


@app.route('/')
def upload_landing():

    return render_template('index.html')


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':

        # Get the submitted project name and file list
        project_name = request.form["project"]
        geocode_helper = request.form["geocode_helper"]
        file_list = request.files.getlist("files")

        print(f"\n\n {geocode_helper} \n\n")

        # Make a path to a subfolder for this session's uploads
        upload_folder = app.config['UPLOAD_FOLDER'] / project_name

        # Upload files if the user provided any
        if file_list[0].filename != '':

            # Make the upload folder if it doesn't exist yet
            if not upload_folder.exists():
                upload_folder.mkdir(parents=True)

            # Save each file to the app's upload folder
            for f in file_list:
                filepath = upload_folder / secure_filename(f.filename)
                f.save(filepath)

        # Execute the actual TMC script!
        xlsx, geojson = write_summary_file(upload_folder,
                                      output_folder=upload_folder,
                                      geocode_helper=geocode_helper)

        zipname = str(geojson.name).replace("tmc_locations_", "").replace(".geojson", "")

        output_zipfile = upload_folder / f"tmc_summary_{zipname}.zip"


        compression = zipfile.ZIP_DEFLATED

        zf = zipfile.ZipFile(output_zipfile, mode="w")
        for f in [xlsx, geojson]:
            if f.exists():
                zf.write(f, f.name, compress_type=compression)
        zf.close()

        return send_file(output_zipfile, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
