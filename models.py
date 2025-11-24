from tortoise import models, fields
from datetime import datetime


class Post(models.Model):
    id = fields.CharField(pk=True, unique=True, null=False, max_length=500)
    price_byn = fields.FloatField(default=0.0, null=True)
    price_usd = fields.FloatField(default=0.0, null=True)
    address = fields.TextField()
    short_description = fields.TextField()
    post_url = fields.TextField()
    date = fields.DatetimeField(default=datetime.now)
    city = fields.TextField(null=False)
    is_sent = fields.BooleanField(null=False, default=False)
    lat = fields.FloatField(null=True)
    lon = fields.FloatField(null=True)

    city_district = fields.TextField(null=True)
    nearby_subway = fields.TextField(null=True, default='')
    nearby_pharmacy = fields.TextField(null=True, default='')
    nearby_kindergarten = fields.TextField(null=True, default='')
    nearby_school = fields.TextField(null=True, default='')
    nearby_bank = fields.TextField(null=True, default='')
    nearby_shop = fields.TextField(null=True, default='')

    rooms = fields.TextField(null=True, default='')
    number_of_floors = fields.TextField(null=True, default='')
    apartment_floor = fields.TextField(null=True, default='')
    total_area = fields.TextField(null=True, default='')
    balcony = fields.TextField(null=True, default='')
    prepayment = fields.TextField(null=True, default='')

    class Meta:
        table = "posts"


class User(models.Model):
    id = fields.TextField(pk=True, null=False)
    is_bot = fields.BooleanField(default=False)
    first_name = fields.TextField()
    is_premium = fields.BooleanField(default=False)

    min_price = fields.FloatField()
    max_price = fields.FloatField()
    city = fields.TextField()
    district = fields.TextField()
    is_active = fields.BooleanField(default=False)
    rooms_count = fields.IntField(default=5)

    class Meta:
        table = "users"


class Image(models.Model):
    id = fields.IntField(pk=True, null=False)
    image_src = fields.TextField()
    loaded_to = fields.TextField(default='/img')
    from_post = fields.ForeignKeyField("models.Post", related_name="images", on_delete=fields.CASCADE)

    class Meta:
        table = "images"



