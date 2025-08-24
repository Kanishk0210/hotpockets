from fireo.models import Model
from fireo.fields import TextField, NumberField, BooleanField, ListField, MapField, DateTime

class CanteenTracker(Model):
    Id = TextField()
    MdfdTmStmp = DateTime()  # matches your existing timestamp field
    CreatedTmStmp = DateTime()  # matches your existing timestamp field
    Type = TextField()
    GameId = TextField()
    GameTrackerId = TextField()
    TxId = TextField(allow_none=True)
    isActive = BooleanField(default=True)
    isBilled = BooleanField(default=False)
    isCancelled = BooleanField(default=False)
    MenuItems = ListField()
    Players = ListField()
    Cost = NumberField(default=0)

    class Meta:
        collection_name = "transaction-data"
