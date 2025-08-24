from fireo.models import Model
from fireo.fields import TextField, NumberField, BooleanField, ListField, MapField, DateTime

class MenuItem(Model):
    Id = TextField()
    Name = TextField()
    Price = NumberField()
    Remaining = NumberField(default=0)
    Ingredients = ListField()
    Type = TextField()  # Added to match your existing schema
    
    class Meta:
        collection_name = "masterdata-target"
