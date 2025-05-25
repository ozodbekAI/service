from rest_framework import serializers
from users.models import User
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'username', 'company_name', 'role', 'is_legal', "password", "date_joined", "profile_image"]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        validated_data['username'] = validated_data.get('username', validated_data['email'])
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)
    

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.is_legal = validated_data.get('is_legal', instance.is_legal)
        instance.company_name = validated_data.get('company_name', instance.company_name)
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        if 'password' in validated_data:
            instance.password = make_password(validated_data['password'])
        instance.save()
        return instance