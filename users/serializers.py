from rest_framework import serializers
from users.models import User
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'username', 'company_name', 'role', 'is_legal', "password", "date_joined"]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        validated_data['username'] = validated_data.get('username', validated_data['email'])
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)