from datetime import datetime
from pytz import timezone
from pathlib import Path
from os import environ
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
SUMMARY_FILE_FOLDER = environ.get("SUMMARY_FILE_FOLDER")


from tmc_app import db, make_random_gradient


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
        folder = self.name
        for bad_char in [" ", "'"]:
            folder = folder.replace(bad_char, "-")
        return folder


class TMCFile(db.Model):

    __tablename__ = 'filedata'

    uid = db.Column(
        db.Integer,
        primary_key=True
    )
    name = db.Column(
        db.Text,
        nullable=False,
        unique=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.uid"),
        nullable=False
    )
    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("userdata.id"),
        nullable=False
    )

    def upload_user(self):
        return User.query.filter_by(id=self.uploaded_by).first()


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
