from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "posts" (
    "id" VARCHAR(500) NOT NULL PRIMARY KEY,
    "price_byn" DOUBLE PRECISION DEFAULT 0,
    "price_usd" DOUBLE PRECISION DEFAULT 0,
    "address" TEXT NOT NULL,
    "short_description" TEXT NOT NULL,
    "post_url" TEXT NOT NULL,
    "date" TIMESTAMPTZ NOT NULL,
    "city" TEXT NOT NULL,
    "is_sent" BOOL NOT NULL DEFAULT False,
    "lat" DOUBLE PRECISION,
    "lon" DOUBLE PRECISION,
    "city_district" TEXT,
    "nearby_subway" TEXT,
    "nearby_pharmacy" TEXT,
    "nearby_kindergarten" TEXT,
    "nearby_school" TEXT,
    "nearby_bank" TEXT,
    "nearby_shop" TEXT,
    "rooms" TEXT,
    "number_of_floors" TEXT,
    "apartment_floor" TEXT,
    "total_area" TEXT,
    "balcony" TEXT,
    "prepayment" TEXT
);
CREATE TABLE IF NOT EXISTS "images" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "image_src" TEXT NOT NULL,
    "loaded_to" TEXT NOT NULL,
    "from_post_id" VARCHAR(500) NOT NULL REFERENCES "posts" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "is_bot" BOOL NOT NULL DEFAULT False,
    "first_name" TEXT NOT NULL,
    "is_premium" BOOL NOT NULL DEFAULT False,
    "min_price" DOUBLE PRECISION NOT NULL,
    "max_price" DOUBLE PRECISION NOT NULL,
    "city" TEXT NOT NULL,
    "district" TEXT NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT False,
    "rooms_count" INT NOT NULL DEFAULT 5
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "w2s3hAw/e323cvq/8Aru8xWw=="
)
