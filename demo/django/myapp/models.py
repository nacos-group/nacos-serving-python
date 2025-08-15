from django.db import models


class User(models.Model):
    """用户模型"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """产品模型"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.name
