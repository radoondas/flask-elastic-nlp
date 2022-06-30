from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class SearchBlogsForm(FlaskForm):
    searchbox = StringField('What are you looking for?', validators=[DataRequired()])
    # searchboxAuthor = StringField('Author', validators=[DataRequired()])
    searchboxAuthor = StringField('Author')
    searchboxBlogWindow = TextAreaField('Text')
    submit = SubmitField('Search')
