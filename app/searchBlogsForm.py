from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class SearchBlogsForm(FlaskForm):
    searchbox = StringField('What are you looking for?',
                            validators=[DataRequired()])
    searchboxAuthor = StringField('Author')
    searchboxBlogWindow = TextAreaField(
        'Which text should I look for answers (QnA)?')
    submit = SubmitField('Search')
    addAuthorButton = SubmitField('+')
