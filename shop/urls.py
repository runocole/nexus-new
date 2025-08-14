from django.urls import path
from .views import (
    ReviewCreateView,
    ReviewDeleteView,
    ReviewDetailView,
    ReviewUpdateView,
    ShopReviewsListView,
    ShopView, 
    ShopDetailView,
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    BatchProductCreateView,
    AllProductsListView,
    ShopUpdateView,
    ShopDeleteView,
    UserReviewsListView,
    NearbyShopsView
)

urlpatterns = [
    path('', ShopView.as_view(), name='shop'),
    path('<uuid:pk>/', ShopDetailView.as_view(), name='shop-detail'),
    path('<uuid:pk>/update/', ShopUpdateView.as_view(), name='shop-update'),
    path('<uuid:pk>/delete/', ShopDeleteView.as_view(), name='shop-delete'),
    path('nearby/', NearbyShopsView.as_view(), name='nearby-shops'),
    # Product URLs
    path('products/', AllProductsListView.as_view(), name='products'),
    path('<uuid:shop_id>/products/', ProductListView.as_view(), name='product-list'),
    path('products/<uuid:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<uuid:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('products/<uuid:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    path('<uuid:shop_id>/products/batch-create/', BatchProductCreateView.as_view(), name='batch-product-create'),

    # Review URLs
    path('<uuid:shop_id>/reviews/', ShopReviewsListView.as_view(), name='shop-reviews'),
    path('reviews/create/', ReviewCreateView.as_view(), name='review-create'),
    path('reviews/<uuid:pk>/', ReviewDetailView.as_view(), name='review-detail'),
    path('reviews/<uuid:pk>/update/', ReviewUpdateView.as_view(), name='review-update'),
    path('reviews/<uuid:pk>/delete/', ReviewDeleteView.as_view(), name='review-delete'),
    path('user/reviews/', UserReviewsListView.as_view(), name='user-reviews'),
]