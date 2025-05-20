from rest_framework import serializers
from users.models import User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(required=True)
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def get_role(self, obj):
        if obj.role == 'admin':
            return 'admin'
        elif obj.role == 'manager':
            return 'staff'
        elif obj.role == 'client':
            return 'client'
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(
            username=validated_data.get('username'),
            email=validated_data.get('email'),
            phone=validated_data.get('phone')
        )
        user.set_password(password)
        user.save()
        return user