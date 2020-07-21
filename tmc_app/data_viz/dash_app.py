"""Instantiate a Dash app."""
import pandas as pd
import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from flask_caching import Cache
from datetime import time, datetime
from dotenv import load_dotenv, find_dotenv
import sqlalchemy
from os import environ
import plotly.express as px

from tmc_app.models import Project

load_dotenv(find_dotenv())
SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")


parameter_style = {
    "font-family": "'Roboto Mono', monospace",
    "color": "cyan",
    "font-weight": "bold",
}

TIMEOUT = 60


def make_nice_txt(v):
    """ Turn 5.25 into '5:15' """
    lookup = {
        "0": "00",
        "25": "15",
        "5": "30",
        "75": "45"
    }
    v = str(float(v))
    h, m = v.split(".")

    minute = lookup[m]

    return f"{h}:{minute}"


def slider_marks():
    # Make a dictionary for our time slider snaps
    slider_marks = {}
    for h in range(0, 24):
        if h > 12:
            ampm = "pm"
            safe_h = h - 12
        else:
            ampm = "am"
            safe_h = h

        slider_marks[h] = {
            "label": f"{safe_h} {ampm}",
            "style": {"transform": "rotate(0deg)",
                       "font-size": '70%'}
        }
    return slider_marks


def pad_minute(m):
    m = str(m)
    if len(m) == 2:
        return f":{m}"
    else:
        return f":0{m}"


def generate_treemap_data(df_timeseries, id_col: str = "location"):
    """
    This function consumes the dataframe from df_timeseries()
    and transforms it to fit the plotly.express.treemap()
    """

    df_timeseries = df_timeseries.copy()

    # Update with a multi-index to include the file id, then remove the fid column
    df_timeseries.set_index([df_timeseries[id_col], df_timeseries.index], inplace=True)
    del df_timeseries[id_col]

    # Stack the dataframe, then reset_index() to explode the multi-index into cols
    df_stacked = pd.DataFrame(
        df_timeseries.stack(), columns=["total"]
    ).reset_index()

    # print(df_timeseries)

    # Remove all rows where the total is zero
    df_filtered = df_stacked[df_stacked.total != 0]

    # Explode the
    attribute_cols = {
        0: "veh_class",
        1: "leg",
        2: "movement"
    }
    df_attrs = df_filtered['level_2'].str.split(
        '_', expand=True
    ).rename(columns=attribute_cols)

    df = pd.concat([df_filtered, df_attrs], axis=1, sort=False)
    # print(df)

    df["hour"] = [str(x.hour) for x in df["time"]]
    df["minute"] = [pad_minute(x.minute) for x in df["time"]]

    for col in ["level_2", "time"]:
        del df[col]

    return df


def timeseries_figure(df_timeries,
                    #   figure_margin: dict = dict(l=20, r=20, t=20, b=20),
                      plot_kwargs: dict = {
                        "facet_col": "location",
                        "facet_col_wrap": 2,
                        "color_discrete_sequence": px.colors.qualitative.Dark24,
                        "facet_row_spacing": 0.04, # default is 0.07 when facet_col_wrap is used
                        "facet_col_spacing": 0.04, # default is 0.03

                       }):
    fig = px.bar(df_timeries, **plot_kwargs)
    # fig.update_layout(margin=figure_margin)
    # fig.layout.plot_bgcolor = "rgba(0,0,0,0)"

    return fig


def treemap_figure(df_treemap,
                   figure_margin: dict = dict(l=20, r=20, t=20, b=20),
                   plot_kwargs: dict = {
                       "values": "total",
                       "path": ["veh_class", "fid", "leg", "movement", "hour", "minute"],
                    }):
    fig = px.treemap(df_treemap, **plot_kwargs)
    fig.update_layout(margin=figure_margin)
    return fig


def create_dashboard(server):
    """Create a Plotly Dash dashboard."""

    # Create the dash app with a connection to the larger Flask app via 'server'
    # --------------------------------------------------------------------------

    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/data-explorer/',
        external_stylesheets=[
                {'href': 'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
                    'rel': 'stylesheet',
                    'integrity': 'sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO',
                    'crossorigin': 'anonymous'
                },
                {'href': 'https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap',
                    'rel': 'stylesheet',
                },
        ]
    )
    dash_app.scripts.config.serve_locally = False
    dcc._js_dist[0]['external_url'] = 'https://cdn.plot.ly/plotly-basic-latest.min.js'

    # Load the initial state of the page
    # ----------------------------------

    # Load up all the projects from the Flask DB into a list of dicts
    active_project = Project.query.first()
    fid_list = [f.uid for f in active_project.files]
    file_options = [{"label": f.name(), "value": f.uid} for f in active_project.files]

    project_options = []
    all_projects = Project.query.all()
    for project in all_projects:
        if project.files:
            project_options.append({"label": project.name,
                                    "value": project.uid})

    # Make a dataframe of the filedata


    # LOAD UP THE DATA AND MAKE THE PLOTS
    # -----------------------------------
    df_timeseries = active_project.generate_timeseries_data()

    df_treemap = generate_treemap_data(df_timeseries, id_col="location")

    kwargs_timeseries = {
        "height": len(fid_list) / 2 * 300,
        "facet_col": "location",
        "facet_col_wrap": 2,
        "color_discrete_sequence": px.colors.qualitative.Dark24
    }



    plot_timeseries = timeseries_figure(df_timeseries, plot_kwargs=kwargs_timeseries)

    kwargs_treeplot = {"path": ["veh_class", "leg", "movement"]}
    plot_tree = treemap_figure(df_treemap, plot_kwargs=kwargs_treeplot)


    # Create Layout
    dash_app.layout = html.Div([
        html.Nav([
            html.A('Exit', className="nav-item nav-link btn btn-outline-primary btn-sm", href='/projects'),
        ], className="nav navbar mb-2"),
        html.Div([
            # Header text with filename and selected start/end times
            html.Div([
                html.H1([
                    "TMC Data Viewer",
                ], className=""),
            ], className="col-8"),
        ], className="row"),
        html.Div([
        ], className="row"),
        html.Div([
            html.Div([
                dcc.RangeSlider(
                    id="range-selector",
                    marks=slider_marks(),
                    min=0,
                    max=24,
                    value=[5, 20],
                    step=0.25,
                    allowCross=False
                ),
            ], className="col-12"),
            html.Div([
                html.H3([
                    "Analyzing ",
                    html.Span(
                        id="txt-name",
                        className="p-2 btn btn-sm btn-secondary mb-2",
                        style=parameter_style
                    ),
                    " from ",
                    html.Span(
                        id="txt-start",
                        className="p-2 btn btn-sm btn-secondary mb-2",
                        style=parameter_style
                    ),
                    " to ",
                    html.Span(
                        id="txt-end",
                        className="p-2 btn btn-sm btn-secondary mb-2",
                        style=parameter_style
                    ),
                ], className=""),
            ], className="col-12 text-center"),
            html.Div([
                html.Span(["Select a project:"]),
                dcc.Dropdown(
                    id='project-selector',
                    options=project_options,
                    value=project_options[0]["value"],
                ),
                html.Br(),
                html.Span("Select modes to include:"),
                dcc.Dropdown(
                    id="mode-selector",
                    options=[
                        {'label': 'Light Vehicles', 'value': 'light'},
                        {'label': 'Heavy Vehicles', 'value': 'heavy'},
                        {'label': 'Bicyclists', 'value': 'bikes'},
                        {'label': 'Pedestrians', 'value': 'peds'},
                    ],
                    multi=True,
                    value=["bikes", "peds", "light", "heavy"],
                    style={"font-size": "0.5rem"}
                ),
                html.Span("Adjust the treemap nesting order:"),
                dcc.Dropdown(
                    id="treemap-path-order",
                    options=[
                        {'label': 'File', 'value': 'location'},
                        {'label': 'Class', 'value': 'veh_class'},
                        {'label': 'Leg', 'value': 'leg'},
                        {'label': 'Movement', 'value': 'movement'},
                        {'label': 'Hour', 'value': 'hour'},
                        {'label': 'Minute', 'value': 'minute'},
                    ],
                    multi=True,
                    value=["location", "leg", "movement", "veh_class"],
                    style={"font-size": "0.7rem"}
                ),
                html.P(id="txt-qaqc", className="mt-2"),
            ], className="col-3 mt-5"),
            html.Div([
                dcc.Graph(
                    id="treemap-graph",
                    figure=plot_tree
                ),
            ], className="col-7"),
        ], className="row"),
        html.Div([
            html.Div([
                dcc.Graph(
                    id="time-bar-graph",
                    figure=plot_timeseries
                ),
            ], className="col"),
        ], className="row"),
    ], className="container")

    init_callbacks(dash_app)
    return dash_app.server


def init_callbacks(dash_app):
    @dash_app.callback([Output('time-bar-graph', 'figure'),
                        Output('treemap-graph', 'figure'),
                        Output('txt-name', 'children'),
                        Output('txt-start', 'children'),
                        Output('txt-end', 'children'),
                        Output('project-selector', 'options'),
                        Output('txt-qaqc', 'children'),
                        ],

                       [Input('project-selector', 'value'),
                        Input('range-selector', 'value'),
                        Input('mode-selector', 'value'),
                        Input('treemap-path-order', 'value'),
                        ])
    def change_project(pid, selected_range, mode_selector, treemap_path_order):
        """
        Triggers
            - User changes the PROJECT selection

        Actions
            - QAQC text 
        """

        project_options = []
        all_projects = Project.query.all()
        for project in all_projects:
            if project.files:
                project_options.append({"label": project.name,
                                        "value": project.uid})

        # WHEN THE PROJECT SELECTION CHANGES, UPDATE FILE LIST OPTIONS
        # ------------------------------------------------------------

        # Get the selected project
        this_project = Project.query.filter_by(uid=pid).first()
        fid_list = [f.uid for f in this_project.files]

        # HANDLE THE TIME SLIDER INPUT
        # ----------------------------

        a, b = selected_range

        a_txt = make_nice_txt(a)
        b_txt = make_nice_txt(b)

        # Make sure that the end time isn't '24:00'
        if b == '24:00':
            b = '23:45'

        df_timeseries = this_project.generate_timeseries_data(
            start_time=a_txt,
            end_time=b_txt,
            fids_to_include=fid_list,
            modes_to_include=mode_selector)

        qaqc_txt = None
        if df_timeseries.shape[0] == 0:
            print("No rows were returned from this query")
            raise PreventUpdate

        df_treemap = generate_treemap_data(df_timeseries)


        # # Don't update the plots if the query returns zero rows
        # if df_timeseries.shape[0] < 1:
        #     plot_timeseries = existing_time_graph
        #     plot_tree = existing_tree_graph
        # else:

        if len(fid_list) % 2 == 1:
            barplot_height = (len(fid_list) + 1) / 2 * 200
            cols = 2
        else:
            barplot_height = len(fid_list) / 2.0 * 200
            cols = 2

        if barplot_height > 1000:
            barplot_height = 1000
            cols = 3

        if not qaqc_txt:
            qaqc_txt = ""

        kwargs_timeseries = {
            "height": barplot_height,
            "facet_col": "location",
            "facet_col_wrap": cols,
            "color_discrete_sequence": px.colors.qualitative.Dark24,
        }
        plot_timeseries = timeseries_figure(df_timeseries, plot_kwargs=kwargs_timeseries)


        if len(treemap_path_order) < 1:
            print("User did not select any options for the treemap nesting order")
            raise PreventUpdate
        else:
            kwargs_treeplot = {"path": treemap_path_order}
            plot_tree = treemap_figure(df_treemap, plot_kwargs=kwargs_treeplot)


        return plot_timeseries, plot_tree, this_project.name, a_txt, b_txt, project_options, qaqc_txt