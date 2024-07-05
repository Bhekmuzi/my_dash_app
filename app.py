# 20204-07-02

# Import dotenv and load variables from .env file
from dotenv import load_dotenv
import os

load_dotenv('variables.env')

# MongoDB Connection URI and Database Name from .env file
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

from pymongo import MongoClient
from datetime import datetime, timedelta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objs as go
import dash_bootstrap_components as dbc

# Connect to MongoDB using environment variables
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
collection = db[MONGODB_COLLECTION]

# Retrieve distinct Home IDs from the collection
home_ids = collection.distinct('home_id')

# Determine the activity level based on active score and norms
def determine_activity_level(active_score, low_norm, norm_score, high_norm):
    if active_score <= low_norm:
        return 'Abnormal', 'red'
    elif low_norm < active_score <= norm_score:
        return 'Low', 'yellow'
    elif norm_score < active_score <= high_norm:
        return 'Active', 'blue'
    elif active_score > high_norm:
        return 'High', 'green'
    else:
        return 'Unknown', 'gray'
    
# Determine the regularity level based on correlation coefficient
def determine_regularity_level(corr_coef):
    if corr_coef < 0.30:
        return 'Abnormal', 'red'
    elif 0.30 <= corr_coef < 0.50:
        return 'Low', 'yellow'
    elif 0.50 <= corr_coef < 0.70:
        return 'Normal', 'blue'
    elif corr_coef >= 0.70:
        return 'High', 'green'
    else:
        return 'Unknown', 'gray'

# Determine the overall status based on the lowest level of activity and regularity
def determine_status(activity_level, regularity_level):
    levels = {'Abnormal': 1, 'Low': 2, 'Normal': 3, 'Active': 4, 'High': 5}
    lowest_level = min(levels[activity_level], levels[regularity_level])

    if lowest_level == 1:
        return 'Attention', 'red'
    elif lowest_level == 2:
        return 'Normal', 'yellow'
    elif lowest_level == 3:
        return 'Normal', 'blue'
    elif lowest_level == 4:
        return 'Active', 'blue'
    elif lowest_level == 5:
        return 'High', 'green'
    else:
        return 'Unknown', 'gray'
        
# Function to retrieve data for a given date and Home ID from MongoDB
def get_data_for_date_and_home(date_str, home_id):
    # print(f"Fetching data for date: {date_str} and home_id: {home_id}")
    try:
        data = collection.find_one({'date': date_str, 'home_id': home_id})
        if data:
            water_consumption = data['water_consumption']
            usage = data['usage']
            norm = data['four_week_usage_norm']
            active_score = data['active_score']
            corr_coef = data['correlation_coefficient']
            low_norm = data['low_norm']
            norm_score = data['norm_active_score']
            high_norm = data['high_norm']
            return {
                'water_consumption': water_consumption,
                'usage': usage,
                'norm': norm,
                'active_score': active_score,
                'corr_coef': corr_coef,
                'low_norm': low_norm,
                'norm_score': norm_score,
                'high_norm': high_norm
            }
        else:
            return None
    except Exception as e:
        # print(f"Error fetching data: {e}")
        return None

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the layout of the app
app.layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Row(
            [
                # Left section for login and date picker
                dbc.Col(
                    width=3,
                    children=[
                        dbc.Button(
                            ">",
                            id="toggle-button",
                            color="primary",
                            className="mb-3",
                        ),
                        dbc.Collapse(
                            id="collapse",
                            is_open=False,
                            children=html.Div(
                                className="border rounded p-3",
                                children=[
                                    html.H5("Login"),
                                    dbc.Input(type="text", placeholder="Username"),
                                    dbc.Input(type="password", placeholder="Password", className="mt-3"),
                                    dbc.Button("Login", color="primary", className="mt-3"),
                                    html.Hr(),
                                    html.H5("Date Picker"), 
                                    # Previous Day Button
                                    html.Button('<', id='prev-day-button', n_clicks=0, style={'display': 'inline-block', 'border': 'none', 'background': 'none', 'marginRight': '10px', 'fontSize': '24px'}),
                                    dcc.DatePickerSingle(
                                        id='date-picker-sidebar',
                                        
                                        min_date_allowed=datetime(2020, 1, 1),
                                        max_date_allowed=datetime.today(),
                                        initial_visible_month=datetime.today() - timedelta(days=1),
                                        date=(datetime.today() - timedelta(days=1)).date(),
                                        display_format='YYYY / M / D',
                                        style={'display': 'inline-block', 'border': 'none', 'fontSize': 18}
                                        # placeholder='Select a date',
                                        # date=None,
                                        # display_format='YYYY-MM-DD',
                                        # className="mt-3"
                                    ),
                                    # Next Day Button
                                    html.Button('>', id='next-day-button', n_clicks=0, style={'display': 'inline-block', 'border': 'none', 'background': 'none', 'marginLeft': '10px', 'fontSize': '24px'}),
                               
                                    # Section for Home ID Picker
                                    html.Div(
                                        children=[
                                            html.H5("Home ID Picker"),
                                            dcc.Dropdown(
                                                id='home-id-picker-sidebar',
                                                options=[{'label': home_id, 'value': home_id} for home_id in home_ids],
                                                value=home_ids[0],  # Default to the first Home ID
                                                style={'width': '100%', 'marginTop': '10px'}
                                            )
                                        ]
                                    )
                                ]
                            )
                        )
                    ]
                ),
                # Right section for displaying figures and title
                dbc.Col(
                    id='right-section',
                    width=9,
                    children=[
                        html.H1('Water Usage Dashboard', style={'textAlign': 'center'}),
                        html.Div(
                            children=[
                                # Previous Day Button
                                # html.Button('<', id='prev-day-button', n_clicks=0, style={'display': 'inline-block', 'border': 'none', 'background': 'none', 'marginRight': '10px', 'fontSize': '24px'}),
                                # # Date Picker
                                # dcc.DatePickerSingle(
                                #     id='date-picker',
                                #     min_date_allowed=datetime(2020, 1, 1),
                                #     max_date_allowed=datetime.today(),
                                #     initial_visible_month=datetime.today() - timedelta(days=1),
                                #     date=(datetime.today() - timedelta(days=1)).date(),
                                #     display_format='YYYY / M / D',
                                #     style={'display': 'inline-block', 'border': 'none', 'fontSize': 18}
                                # ),
                                # # Next Day Button
                                # html.Button('>', id='next-day-button', n_clicks=0, style={'display': 'inline-block', 'border': 'none', 'background': 'none', 'marginLeft': '10px', 'fontSize': '24px'}),
                               
                                # Home ID Picker
                                # html.P(id='HomeId', style={'fontSize': 18}),
                                # dcc.Dropdown(
                                #     id='home-id-picker',
                                #     options=[{'label': home_id, 'value': home_id} for home_id in home_ids],
                                #     value=home_ids[0],  # Default to the first Home ID
                                #     style={'width': '120px', 'display': 'inline-block', 'marginRight': '10px'}
                                # ),

                                # Status and Shape
                                html.Div(children=[
                                    html.P(id='status', style={'fontSize': 18}),
                                    dcc.Graph(
                                        id='status-rect',
                                        config={'displayModeBar': False}
                                    )
                                ], style={'display': 'inline-block', 'verticalAlign': 'middle', 'marginRight': '10px'}),
                        
                                # Activity Level and Shape
                                html.Div(children=[
                                    html.P(id='activity-level', style={'fontSize': 18}),
                                    dcc.Graph(
                                        id='activity-circle',
                                        config={'displayModeBar': False}
                                    )
                                ], style={'display': 'inline-block', 'verticalAlign': 'middle', 'marginRight': '10px'}),
                                
                                # Regularity Level and Shape
                                html.Div(children=[
                                    html.P(id='regularity-level', style={'fontSize': 18}),
                                    dcc.Graph(
                                        id='regularity-circle',
                                        config={'displayModeBar': False}
                                    )
                                ], style={'display': 'inline-block', 'verticalAlign': 'middle', 'marginRight': '10px'}),
                            ],
                            style={'textAlign': 'center', 'marginBottom': '20px'}
                        ),

                        html.Div(
                            id='right-section-content',
                            # className='border rounded p-3',
                            children=[
                                html.H5("Water usage pattern"),
                                # className='center-title',  # Apply the center-title class
                                dcc.Graph(
                                    id='usage-graph',
                                    figure={
                                        'data': [],
                                        'layout': go.Layout(
                                            title='Usage',
                                            height=250,
                                            xaxis={'title': 'Time'},
                                            yaxis={'title': 'Usage'}
                                        )
                                    }
                                ),
                                html.Div(
                                    children=[
                                        html.H5("Four Week Water Usage Norm"),
                                        dcc.Graph(
                                            id='norm-graph',
                                            figure={
                                                'data': [],
                                                'layout': go.Layout(
                                                    title='Norm',
                                                    height=300,
                                                    xaxis={'title': 'Time'},
                                                    yaxis={'title': 'Norm'}
                                                )
                                            }
                                        )
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.H5("Water consumption"),
                                        dcc.Graph(
                                            id='water-consumption-graph',
                                            figure={
                                                'data': [],
                                                'layout': go.Layout(
                                                    title='Water consumption',
                                                    height=300,
                                                    xaxis={'title': 'Time'},
                                                    yaxis={'title': 'Water consumption'}
                                                )
                                            }
                                        )
                                    ]
                                ),
                                html.Div(
                                    id='print-output',
                                    className='mt-3'
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    ]
)

# Callback to update graphs based on date and home ID selection
@app.callback(
    [Output('status', 'children'), Output('status-rect', 'figure'),
     Output('activity-level', 'children'), Output('activity-circle', 'figure'),
     Output('regularity-level', 'children'), Output('regularity-circle', 'figure'),
     Output('usage-graph', 'figure'), Output('norm-graph', 'figure'),
     Output('water-consumption-graph', 'figure')], [Input('date-picker-sidebar', 'date'),
     Input('home-id-picker-sidebar', 'value')]
)
def update_graphs(selected_date, selected_home_id):
    if selected_date and selected_home_id:
        # Convert selected_date to YYYY-MM-DD format
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        # Calculate previous day's date
        previous_day_date_str = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
             
        # Fetch data using previous_day_date_str and selected_home_id
        data = get_data_for_date_and_home(previous_day_date_str, selected_home_id)
        if data:
            usage_data = data['usage']
            norm_data = data['norm']
            water_consumption_data = data['water_consumption']
            active_score = data['active_score']
            corr_coef = data['corr_coef']
            low_norm = data['low_norm']
            norm_score = data['norm_score']
            high_norm = data['high_norm']
            
            # Determine levels and status
            activity_level, activity_color = determine_activity_level(active_score, low_norm, norm_score, high_norm)
            regularity_level, regularity_color = determine_regularity_level(corr_coef)
            status, status_color = determine_status(activity_level, regularity_level)
            
            # Create a time series for x-axis
            time_series = list(range(1, len(usage_data) + 1))

            # Custom status, activity, and regularity figures
            status_text = 'Status' #f'Status: {status}'
            status_rect_figure = go.Figure(
                data=[go.Scatter(
                    x=[0], y=[0], text=[status],
                    mode='text',
                    textfont=dict(size=16, color=status_color)
                )],
                layout=go.Layout(
                    shapes=[
                        go.layout.Shape(
                            type="path",
                            path='M -0.5 -0.25 L 0.5 -0.25 Q 0.6 -0.25 0.6 -0.15 L 0.6 0.15 Q 0.6 0.25 0.5 0.25 L -0.5 0.25 Q -0.6 0.25 -0.6 0.15 L -0.6 -0.15 Q -0.6 -0.25 -0.5 -0.25 Z',
                            line=dict(color=status_color),
                            fillcolor='rgba(0,0,0,0)'
                        )
                    ],
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    height=80,
                    width=150,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
            )

            activity_level_text = 'Activity Level' #f'Activity Level: {activity_level}'
            activity_circle_figure = go.Figure(
                data=[go.Scatter(
                    x=[0], y=[0], text=['AS'],
                    mode='text',
                    textfont=dict(size=16, color=activity_color)
                )],
                layout=go.Layout(
                    shapes=[
                        go.layout.Shape(
                            type='circle',
                            x0=-0.5, y0=-0.5,
                            x1=0.5, y1=0.5,
                            line=dict(color=activity_color),
                            fillcolor='rgba(0,0,0,0)'
                        )
                    ],
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    height=80,
                    width=80,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
            )

            regularity_level_text = 'Regularity Level' # f'Regularity Level: {regularity_level}'
            regularity_circle_figure = go.Figure(
                data=[go.Scatter(
                    x=[0], y=[0], text=['CC'],
                    mode='text',
                    textfont=dict(size=16, color=regularity_color)
                )],
                layout=go.Layout(
                    shapes=[
                        go.layout.Shape(
                            type='circle',
                            x0=-0.5, y0=-0.5,
                            x1=0.5, y1=0.5,
                            line=dict(color=regularity_color),
                            fillcolor='rgba(0,0,0,0)'
                        )
                    ],
                    xaxis=dict(visible=False),
                    yaxis=dict(visible=False),
                    height=80,
                    width=80,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
            )

            # Update Data Display 1: Usage
            figure_usage = {
                'data': [
                    go.Bar(x=time_series, y=usage_data, name='Usage')
                ],
                'layout': go.Layout(
                    # title=f'Usage for Date: {previous_day_date_str}'
                    title=f'Active Score: {data["active_score"]} | Correlation Coefficient: {data["corr_coef"]}',
                    xaxis={'title': 'Time'},
                    yaxis={'title': 'Usage'}
                )
            }
            
            # Update Data Display 2: Norm
            figure_norm = {
                'data': [
                    go.Bar(x=time_series, y=norm_data, name='Norm')
                ],
                'layout': go.Layout(
                    # title=f'Norm for Date: {previous_day_date_str}',
                    title=f'Low norm: {data["low_norm"]} | Norm: {data["norm_score"]} | High norm: {data["high_norm"]}',
                    xaxis={'title': 'Time'},
                    yaxis={
                        'title': 'Norm',
                        'range': [0, 100]
                    }
                )
            }
          
            # Update Data Display 3: Water consumption
            figure_water_consumption = {
                'data': [
                    go.Bar(x=time_series, y=water_consumption_data, name='Water consumption', marker=dict(color='orange'))
                ],
                'layout': go.Layout(
                    title=f'Water consumption for Date: {previous_day_date_str}',
                    xaxis={'title': 'Time'},
                    yaxis={'title': 'volume (L/15min)'}
                )
            }

            return (
                status_text, status_rect_figure,
                activity_level_text, activity_circle_figure,
                regularity_level_text, regularity_circle_figure,
                figure_usage, figure_norm, figure_water_consumption
                # f'Usage: {usage_data}, Norm: {norm_data}, Water consumption: {water_consumption_data}'
            )
    
    # Default empty figures and print output
    return (
        '', go.Figure(),
        '', go.Figure(),
        '', go.Figure(),
        go.Figure(),
        go.Figure(),
        go.Figure(),
        ''
    )

# Callback to toggle the collapse state and expand right section width
@app.callback(
    [Output("collapse", "is_open"),
     Output("right-section", "width")],
    [Input("toggle-button", "n_clicks")],
    [State("collapse", "is_open"),
     State("right-section", "width")]
)
def toggle_collapse_and_expand_right_section(n, is_open, right_width):
    if n:
        is_open = not is_open
        if is_open:
            return is_open, 9
        else:
            return is_open, 12
    return is_open, right_width

# Callbacks for previous and next day buttons
@app.callback(
    Output("date-picker-sidebar", "date"),
    [Input("prev-day-button", "n_clicks"), Input("next-day-button", "n_clicks")],
    [State("date-picker-sidebar", "date")]
    # Output('date-picker', 'date'),
    # [Input('prev-day-button', 'n_clicks'),
    #  Input('next-day-button', 'n_clicks')],
    # [State('date-picker', 'date')]
)
def update_date(prev_clicks, next_clicks, current_date):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'No clicks yet'
        return current_date
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    current_date = datetime.strptime(current_date, '%Y-%m-%d')

    if button_id == 'prev-day-button':
        new_date = current_date - timedelta(days=1)
    elif button_id == 'next-day-button':
        new_date = current_date + timedelta(days=1)
    else:
        new_date = current_date

    return new_date.strftime('%Y-%m-%d')

if __name__ == '__main__':
    app.run_server(debug=True)
