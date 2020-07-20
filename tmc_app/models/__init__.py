from datetime import datetime
from pytz import timezone
from pathlib import Path
from os import environ
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
import pandas as pd

from tmc_app import db, make_random_gradient

load_dotenv(find_dotenv())
SUMMARY_FILE_FOLDER = environ.get("SUMMARY_FILE_FOLDER")
RAW_DATA_FOLDER = environ.get("RAW_DATA_FOLDER")
SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")

class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = 'userdata'

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )
    email = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )
    password = db.Column(
        db.String(200),
        primary_key=False,
        unique=False,
        nullable=False
    )
    website = db.Column(
        db.String(60),
        index=False,
        unique=False,
        nullable=True
    )
    created_on = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=True,
        default=datetime.now(timezone("US/Eastern")),
    )
    last_login = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=True
    )
    background = db.Column(
        db.Text,
        nullable=False,
        unique=False,
        default=make_random_gradient()
    )

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(
            password,
            method='sha256'
        )

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def track_login(self):
        """Set the last_login value to now """
        self.last_login = datetime.now(timezone("US/Eastern"))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def projects_created(self):
        # projects_from_this_user = []
        # for project in Project.query.all():
        #     if project.created_by == self.id:
        #         projects_from_this_user.append(project)
        # return projects_from_this_user
        return Project.query.filter_by(
            created_by=self.id
        ).all()

    def num_projects_created(self):
        return len(self.projects_created())


class Project(db.Model):

    __tablename__ = 'projects'

    uid = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )
    description = db.Column(
        db.Text,
        nullable=False,
        unique=False
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("userdata.id"),
        nullable=False
    )
    background = db.Column(
        db.Text,
        nullable=False,
        unique=False,
        default=make_random_gradient
    )

    files = db.relationship("TMCFile", backref=__tablename__, lazy=True)
    output_files = db.relationship("OutputFile", backref=__tablename__, lazy=True)

    def num_files(self):
        return len(self.files)

    def file_uploaders(self):
        all_uploaders = []
        all_uploader_ids = []
        for f in self.files:
            user_id = int(f.uploaded_by)
            if user_id not in all_uploader_ids:

                user = User.query.filter_by(id=user_id).first()
                all_uploader_ids.append(user_id)
                all_uploaders.append(user)

        return all_uploaders

    def created_by_user(self):
        return User.query.filter_by(id=self.created_by).first()

    def safe_folder_name(self):

        # TODO make sure number is not first character
        # TODO learn regex

        no_dice = [
            " ", "'", "`", "~", "!", "@", "#", "$",
            "%", "^", "&", "*", "(", ")", "[", "]",
            "{", "}", ";", "=", ",", ".", "/", r"\\",
            "|", "?", "+",
        ]

        folder = self.name
        for char in no_dice:
            folder = folder.replace(char, "_")
        return folder.lower()

    def folder_path(self):
        return Path(RAW_DATA_FOLDER) / self.safe_folder_name()

    def create_project_table(self,
                             uri: str = SQLALCHEMY_DATABASE_URI,):

        all_dfs = []

        for f in self.files:
            engine = create_engine(uri)
            df = pd.read_sql(f"SELECT * FROM data_p{self.uid}_f{f.uid}", engine, index_col="time")
            engine.dispose()
            all_dfs.append(df)

        df = pd.concat(all_dfs)

        engine = create_engine(uri)
        df.to_sql(f"data_merged_p{self.uid}", engine, if_exists="replace")
        engine.dispose()

    def generate_timeseries_data(self,
                                 fids_to_include: list = None,
                                 uri: str = SQLALCHEMY_DATABASE_URI,
                                 start_time: str = "5:00",
                                 end_time: str = "20:00",
                                 modes_to_include: list = ["heavy", "light", "bikes", "peds"]):
        """
        This function creates a dataframe that is tailored to plotly.express.bar()
        """

        if not fids_to_include:
            fids_to_include = [f.uid for f in self.files]

        fids_to_include = [str(x) for x in fids_to_include]

        engine = create_engine(uri)
        df_sample = pd.read_sql(f"SELECT * FROM data_merged_p{self.uid} LIMIT 1", uri)
        engine.dispose()

        q = "SELECT time, CASE WHEN f.title IS NULL THEN f.filename ELSE f.title END AS location, "

        for col in df_sample.columns:
            if col != 'fid':

                # Confirm it's in the mode list
                wt = col.split("_")[0]
                if wt in modes_to_include:
                    q += f" {col}, "

        q = q[:-2] + f" FROM data_merged_p{self.uid}"

        q += " LEFT JOIN filedata f on f.uid = fid"

        q += f"""
            WHERE time >= '{start_time}'
                AND time < '{end_time}'
                AND fid IN ({", ".join(fids_to_include)}) """

        engine = create_engine(uri)
        df = pd.read_sql(q, uri, index_col="time")
        engine.dispose()

        return df


class TMCFile(db.Model):

    __tablename__ = 'filedata'

    uid = db.Column(
        db.Integer,
        primary_key=True
    )
    filename = db.Column(
        db.Text,
        nullable=False,
        unique=False
    )
    title = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.uid"),
        nullable=False
    )
    model_id = db.Column(
        db.Integer,
        nullable=True
    )
    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("userdata.id"),
        nullable=False
    )
    lat = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )
    lng = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )
    data_date = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=True
    )
    legs = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )
    start_time = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )
    end_time = db.Column(
        db.Text,
        nullable=True,
        unique=False
    )

    def name(self):
        if self.title:
            return self.title
        else:
            return self.filename

    def upload_user(self):
        return User.query.filter_by(id=self.uploaded_by).first()

    def filepath(self):
        project = Project.query.filter_by(uid=self.project_id).first()

        return Path(RAW_DATA_FOLDER) / project.safe_folder_name() / self.filename

    def extract_metadata(self):
        location_kwargs = {
            "sheet_name": "Information",
            "header": None,
            "usecols": "A:B",
            "names": ["place_type", "place_name"]
        }

        df_location = pd.read_excel(self.filepath(), **location_kwargs).dropna()

        location_kwargs["usecols"] = "D:E"
        location_kwargs["names"] = ["time_type", "time_value"]

        df_time = pd.read_excel(self.filepath(), **location_kwargs).dropna()

        data_date = None
        start_time = ""
        end_time = ""
        location_name = ""
        legs = {}

        # Get the location_name and leg names
        for _, row in df_location.iterrows():

            if row.place_type == "Intersection Name":
                location_name = row.place_name
            else:
                legs[row.place_type.lower()] = row.place_name

        # Get the date and start/end times
        for _, row in df_time.iterrows():

            if row.time_type == "Date":
                data_date = row.time_value
            elif row.time_type == "Start Time":
                start_time = row.time_value
            elif row.time_type == "End Time":
                end_time = row.time_value

        return {
            "location_name": location_name,
            "legs": legs,
            "data_date": data_date,
            "start_time": start_time,
            "end_time": end_time,
        }


class OutputFile(db.Model):
    __tablename__ = 'outputfiledata'

    uid = db.Column(
        db.Integer,
        primary_key=True
    )
    filename = db.Column(
        db.Text,
        nullable=False,
        unique=True
    )
    analysis_type = db.Column(
        db.String(50),
        nullable=False,
        unique=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.uid"),
        nullable=False
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("userdata.id"),
        nullable=False
    )
    created_on = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=False,
        default=datetime.now(timezone("US/Eastern")),
    )

    def created_user(self):
        return User.query.filter_by(id=self.created_by).first()

    def fancy_create_date(self):
        return self.created_on.strftime("%b %d %Y %H:%M:%S")

    def hard_code_path(self):

        return Path(SUMMARY_FILE_FOLDER) / self.filename()
