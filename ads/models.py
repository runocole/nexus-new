from django.db import models
from shop.models import Shop
from django.utils import timezone
from authentication.models import User
import uuid

class Ad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='ads')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['shop']),
            models.Index(fields=['is_active']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"Ad for {self.shop.name} from {self.start_date} to {self.end_date}"
    
    def save(self, *args, **kwargs):
        if self.end_date < timezone.now():
            self.is_active = False
        super().save(*args, **kwargs)
        
class Payment(models.Model):
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, null=True, blank=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.PositiveIntegerField(default=5000)  
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    # Paystack specific fields
    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    authorization_url = models.URLField(null=True, blank=True)
    access_code = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    verified = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['ad']),
            models.Index(fields=['owner']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        shop_name = self.shop.name if self.shop else "No shop"
        return f"{self.owner.username} made payment of {self.amount} for {shop_name} (Status: {self.payment_status})"