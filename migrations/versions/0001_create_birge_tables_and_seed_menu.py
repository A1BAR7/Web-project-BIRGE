"""Create Birge tables and seed menu

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


# Frozen Assignment 5 menu and photo attribution.
MENU_COLUMNS = ['id',
 'name',
 'description',
 'price',
 'currency',
 'category',
 'canteen',
 'image_url',
 'available',
 'image_kind',
 'image_alt',
 'image_credit',
 'image_source']


 
MENU_ROWS = [(10001,
  'Супер комбо 3',
  '3 донера + 3 айрана',
  4820,
  'KZT',
  'Combo',
  'SDU-Red canteen',
  '/static/images/food/doner-combo-three.jpg',
  True,
  'authentic',
  'Супер комбо 3',
  'Жобаға берілген фото',
  'Photo/супер комбо3.jpg'),
 (10002,
  'Комбо 2',
  '2 донера + 2 айрана',
  2860,
  'KZT',
  'Combo',
  'SDU-Red canteen',
  '/static/images/food/doner-combo-two.jpg',
  True,
  'authentic',
  'Комбо 2',
  'Жобаға берілген фото',
  'Photo/комбо2.jpg'),
 (10003,
  'Пицца Маргарита',
  '',
  2450,
  'KZT',
  'Pizza',
  'SDU-Red canteen',
  '/static/images/food/pizza-margherita.jpg',
  True,
  'authentic',
  'Пицца Маргарита',
  'Жобаға берілген фото',
  'Photo/маргарита.jpg'),
 (10004,
  'Пицца Пепперони',
  '',
  2450,
  'KZT',
  'Pizza',
  'SDU-Red canteen',
  '/static/images/food/pizza-pepperoni.jpg',
  True,
  'authentic',
  'Пицца Пепперони',
  'Жобаға берілген фото',
  'Photo/пепперони.jpg'),
 (10005,
  'Пиде тауық етімен',
  '',
  1750,
  'KZT',
  'Pide',
  'SDU-Red canteen',
  '/static/images/food/chicken-pide.jpg',
  True,
  'authentic',
  'Пиде тауық етімен',
  'Жобаға берілген фото',
  'Photo/пиде.jpg'),
 (10006,
  'Хот-дог',
  '',
  1100,
  'KZT',
  'Fast Food',
  'SDU-Red canteen',
  '/static/images/food/hot-dog.jpg',
  True,
  'authentic',
  'Хот-дог',
  'Жобаға берілген фото',
  'Photo/хот-дог.jpg'),
 (10007,
  'Капсалон',
  '',
  1690,
  'KZT',
  'Fast Food',
  'SDU-Red canteen',
  '/static/images/food/kapsalon.jpg',
  True,
  'authentic',
  'Капсалон',
  'Жобаға берілген фото',
  'Photo/капсолон.jpg'),
 (10008,
  'Гуйру лағман',
  '',
  1590,
  'KZT',
  'Main Course',
  'Injoo',
  '/static/images/food/guyru-lagman.jpg',
  True,
  'authentic',
  'Гуйру лағман',
  'Жобаға берілген фото',
  'Photo/гуйру.jpg'),
 (10009,
  'Суйру лағман',
  '',
  1590,
  'KZT',
  'Main Course',
  'Injoo',
  '/static/images/food/suyru-lagman.jpg',
  True,
  'authentic',
  'Суйру лағман',
  'Жобаға берілген фото',
  'Photo/Суйру.jpg'),
 (10010,
  'Сет SDU',
  '30 штук суши + 1 пицца + 1 л колы',
  8900,
  'KZT',
  'Combo',
  'Maki Maki',
  '/static/images/food/sdu-sushi-pizza-combo.jpg',
  True,
  'authentic',
  'Сет SDU',
  'Жобаға берілген фото',
  'Photo/сет SDU.jpg')]


def upgrade():
    op.create_table('confessions',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('text', sa.String(length=280), nullable=False),
        sa.Column('author_id', sa.BigInteger(), nullable=False),
        sa.CheckConstraint('author_id > 0', name='ck_confession_author'),
        sa.PrimaryKeyConstraint('id')
    )
    food_items = op.create_table('food_items',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), sa.Identity(start=10011), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=False),
        sa.Column('price', sa.Float(precision=53), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('canteen', sa.String(length=100), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('available', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('image_kind', sa.String(length=14), nullable=False),
        sa.Column('image_alt', sa.Text(), nullable=False),
        sa.Column('image_credit', sa.Text(), nullable=False),
        sa.Column('image_source', sa.Text(), nullable=False),
        sa.CheckConstraint("currency = 'KZT'", name='ck_food_currency'),
        sa.CheckConstraint("image_kind IN ('placeholder', 'representative', 'authentic')", name='ck_food_image_kind'),
        sa.CheckConstraint('length(trim(name)) > 0 AND length(trim(category)) > 0 AND length(trim(canteen)) > 0', name='ck_food_labels'),
        sa.CheckConstraint('price > 0 AND price <= 1.7976931348623157e308', name='ck_food_price'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('lost_items',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=5), nullable=False),
        sa.Column('place', sa.String(length=120), nullable=False),
        sa.Column('desc', sa.String(length=500), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('resolved', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("status IN ('lost', 'found')", name='ck_lost_status'),
        sa.CheckConstraint('owner_id > 0', name='ck_lost_owner'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('skills',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('person', sa.String(length=60), nullable=False),
        sa.Column('kind', sa.String(length=5), nullable=False),
        sa.Column('detail', sa.String(length=500), nullable=False),
        sa.Column('exchange', sa.String(length=120), nullable=False),
        sa.Column('owner_id', sa.BigInteger(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("kind IN ('teach', 'learn')", name='ck_skill_kind'),
        sa.CheckConstraint('owner_id > 0', name='ck_skill_owner'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('confession_likes',
        sa.Column('post_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.CheckConstraint('user_id > 0', name='ck_like_user'),
        sa.ForeignKeyConstraint(['post_id'], ['confessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id', 'user_id')
    )
    op.create_table('lost_item_images',
        sa.Column('position', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('item_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('url', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['lost_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('position'),
        sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_lost_item_images_item_id'), 'lost_item_images', ['item_id'], unique=False)
    op.create_table('skill_requests',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('skill_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('applicant_id', sa.BigInteger(), nullable=False),
        sa.Column('message', sa.String(length=300), nullable=False),
        sa.Column('status', sa.String(length=8), server_default='pending', nullable=False),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name='ck_request_status'),
        sa.CheckConstraint('applicant_id > 0', name='ck_request_applicant'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_requests_skill_id'), 'skill_requests', ['skill_id'], unique=False)
    op.create_index('uq_skill_requests_pending', 'skill_requests', ['skill_id', 'applicant_id'], unique=True, postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))

    op.bulk_insert(food_items, [dict(zip(MENU_COLUMNS, row)) for row in MENU_ROWS])


def downgrade():
    op.drop_index('uq_skill_requests_pending', table_name='skill_requests', postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.drop_index(op.f('ix_skill_requests_skill_id'), table_name='skill_requests')
    op.drop_table('skill_requests')
    op.drop_index(op.f('ix_lost_item_images_item_id'), table_name='lost_item_images')
    op.drop_table('lost_item_images')
    op.drop_table('confession_likes')
    op.drop_table('skills')
    op.drop_table('lost_items')
    op.drop_table('food_items')
    op.drop_table('confessions')
