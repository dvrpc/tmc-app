"""Instantiate a Dash app."""
import numpy as np
import pandas as pd
import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

from tmc_app.models import (
    Project,
    TMCFile
)

from tmc_summarizer import TMC_File as TMC_Raw_Data

parameter_style = {
    "font-family": "'Roboto Mono', monospace",
    "color": "red",
    "font-weight": "bold",
}


def make_treemap_figure(df, path_order=['wt', 'leg', 'movement']):
    df.rename(columns={0: "total"}, inplace=True)

    fig = px.treemap(df, path=path_order, values="total", width=800, height=400)

    return fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))


def make_faceted_bar_plot(df):
    df.rename(columns={0: "total"}, inplace=True)
    return px.bar(df, x="movement", y="total", barmode="group",
                  facet_row="leg", facet_col="wt",
                  category_orders={"wt": ["Heavy", "Light", "Bikes", "Peds"],
                                    "leg": ["NB", "SB", "EB", "WB"],
                                    "movement": ["U", "Left", "Thru", "Right", "Xwalk"]})


def make_timeseries_bar_plot(df):
    df.rename(columns={0: "total"}, inplace=True)
    return px.bar(df, height=400, color_discrete_sequence=px.colors.qualitative.Dark24)


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



def create_dashboard(server):
    """Create a Plotly Dash dashboard."""
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix='/data-viewer/',
        external_stylesheets=[
                {'href': 'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
                    'rel': 'stylesheet',
                    'integrity': 'sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO',
                    'crossorigin': 'anonymous'
                },
                {'href': 'https://fonts.googleapis.com/css2?family=Roboto+Mono&display=swap',
                    'rel': 'stylesheet',
                },
            '/static/css/dash_app.css',
        ]
    )
    dash_app.scripts.config.serve_locally = False
    dcc._js_dist[0]['external_url'] = 'https://cdn.plot.ly/plotly-basic-latest.min.js'

    # Load up all the projects into a list of dicts

    file_options = [{"label": "All files for this project", "value": "all"}]
    project_options = []
    projects_with_files = []
    for project in Project.query.all():
        if project.files:
            projects_with_files.append(project)
            project_options.append(
                {"label": project.name, "value": project.uid}
            )
            for f in project.files:
                file_options.append(
                    {"label": f.name, "value": f.uid}
                )

    # # Load DataFrame
    first_file = projects_with_files[0].files[0]
    tmc = TMC_Raw_Data(first_file.filepath())
    df_treemap = tmc.treemap_df("5:00", "20:00")
    full_time_df = tmc.all_raw_data()

    filtered_time_df = tmc.filter_df_by_start_end_time(full_time_df, "5:00", "20:00")

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

    # Create Layout
    dash_app.layout = html.Div([
        html.Nav([
            html.A('Exit', className="nav-item nav-link btn btn-outline-primary btn-sm", href='/my-projects'),
        ], className="nav navbar"),
        html.Div([
            # Header text with filename and selected start/end times
            html.Div([
                html.H3([
                    "Analyzing ",
                    html.Span(
                        id="file-txt",
                        className="p-2 btn btn-sm btn-light mb-2",
                        style=parameter_style
                    ),
                    " from ",
                    html.Span(
                        id="start-time",
                        className="p-2 btn btn-sm btn-light mb-2",
                        style=parameter_style
                    ),
                    " to ",
                    html.Span(
                        id="end-time",
                        className="p-2 btn btn-sm btn-light mb-2",
                        style=parameter_style
                    ),
                ], className=""),
            ], className="col- 8"),
            html.Div([
                dcc.Dropdown(
                    id='project-selector',
                    options=project_options,
                    value=project_options[0]["value"],
                ),
            ], className="col-4"),
        ], className="row"),
        html.Div([
        ], className="row"),
        html.Div([
            html.Div([
                dcc.RangeSlider(
                    id="range-selector",
                    marks=slider_marks,#{i: f'{i}' for i in range(0, 24)},
                    min=0,
                    max=24,
                    value=[5, 20],
                    step=0.25,
                    allowCross=False
                ),
            ], className="col-12"),
            html.Div([
                html.Br(), html.Br(),
                html.Span(["Select a file from this project:"],),
                dcc.Dropdown(
                    id='file-selector',
                    options=file_options,
                    value=file_options[1]["value"],
                    style={"font-size": "0.5rem"}
                ),
                html.Span("Choose modes to include:"),
                dcc.Dropdown(
                    id="mode-selector",
                    options=[
                        {'label': 'Light Vehicles', 'value': 'Light'},
                        {'label': 'Heavy Vehicles', 'value': 'Heavy'},
                        {'label': 'Bicyclists', 'value': 'Bikes'},
                        {'label': 'Pedestrians', 'value': 'Peds'},
                    ],
                    multi=True,
                    value=["Light", "Heavy", "Bikes", "Peds"],
                    style={"font-size": "0.5rem"}
                ),
                html.Span("Adjust the treemap nesting order:"),
                dcc.Dropdown(
                    id="treemap-path-order",
                    options=[
                        {'label': 'Class', 'value': 'wt'},
                        {'label': 'Leg', 'value': 'leg'},
                        {'label': 'Movement', 'value': 'movement'}
                    ],
                    multi=True,
                    value=["leg", "movement", "wt"],
                    style={"font-size": "0.7rem"}
                ),
            ], className="col-3 mt-5"),
            html.Div([
                dcc.Graph(
                    id="treemap-graph",
                    figure=make_treemap_figure(df_treemap)
                ),
            ], className="col-7"),
        ], className="row"),
        html.Div([
            html.Div([
                dcc.Graph(
                    id="time-bar-graph",
                    figure=make_timeseries_bar_plot(filtered_time_df)
                ),
            ], className="col"),
        ], className="row"),
        html.Div([
            html.Div([
                dcc.Graph(
                    id="facet-bar-graph",
                    figure=make_faceted_bar_plot(df_treemap)
                ),
            ], className="col"),
        ], className="row"),
    ], className="container")

    init_callbacks(dash_app)

    return dash_app.server


def init_callbacks(dash_app):
    @dash_app.callback([Output('start-time', 'children'),
                        Output('end-time', 'children'),
                        Output('treemap-graph', 'figure'),
                        Output('facet-bar-graph', 'figure'),
                        Output('time-bar-graph', 'figure'),
                        Output('file-txt', 'children'),
                        Output('project-selector', 'options'),
                        Output('file-selector', 'options'),
                        ],

                       [Input('project-selector', 'value'),
                        Input('range-selector', 'value'),
                        Input('file-selector', 'value'),
                        Input('treemap-path-order', 'value'),
                        ])
    def update_ph_selection_text(project_id, selected_range, file_id, treemap_order):

        this_project = Project.query.filter_by(uid=project_id).first()

        if file_id == "all":
            file_txt = f"all {this_project.name} files"
        elif file_id == "no files":
            file_txt = "No files have been uploaded for this project yet"
        else:
            this_file = TMCFile.query.filter_by(uid=file_id).first()
            file_txt = this_file.name

        file_options = [{"label": "Analyze all files for this project", "value": "all"}]
        file_options += [{"label": f.name, "value": f.uid} for f in this_project.files]

        project_options = [{"label": p.name, "value": p.uid} for p in Project.query.all() if p.files]

        file_object = TMCFile.query.filter_by(uid=file_id).first()

        a, b = selected_range


        a = make_nice_txt(a)
        b = make_nice_txt(b)

        # Make sure that the end time isn't '24:00'
        if b == '24:00':
            b = '23:45'

        tmc = TMC_Raw_Data(file_object.filepath())

        # Treemap and faceted bar plot use the same df
        tree_df = tmc.treemap_df(a, b)
        treemap_figure = make_treemap_figure(tree_df, path_order=treemap_order)
        facet_barplot = make_faceted_bar_plot(tree_df)

        # Time series uses the full dataframe
        time_df = tmc.all_raw_data()
        filtered_time_df = tmc.filter_df_by_start_end_time(time_df, a, b)

        time_barplot = make_timeseries_bar_plot(filtered_time_df)

        return ([a], [b],
                treemap_figure, facet_barplot, time_barplot,
                file_txt, project_options, file_options)


def create_data_table(df):
    """Create Dash datatable from Pandas DataFrame."""
    table = dash_table.DataTable(
        id='treemap-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        sort_action="native",
        sort_mode='native',
        page_size=300
    )
    return table


def load_tmc_file(f: TMCFile) -> TMC_Raw_Data:

    return TMC_Raw_Data(f.filepath(), geocode_helper="Bristol, PA")
