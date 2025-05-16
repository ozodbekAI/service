from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from users.models import User
from users.serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import make_password
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny,]

    @extend_schema(
        request=UserSerializer,
        responses={201: UserSerializer},
        description='Register a new user',
        tags=["Users"],
        examples=[
            OpenApiExample(
                'User Registration Example',
                value={
                    'email': 'user@example.com',
                    'username': 'username',
                    'phone': '+998901234567',
                    'password': 'securepassword'
                },
                request_only=True,
            )
        ]
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


    @extend_schema(
        request=OpenApiExample(
            'Login Request',
            value={
                'email': 'user@example.com',
                'password': 'securepassword'
            }
        ),
        tags=["Users"],
        responses={
            200: OpenApiResponse(
                response=OpenApiExample(
                    'Login Response',
                    value={
                        'user': {
                            'id': 1,
                            'username': 'username',
                            'email': 'user@example.com',
                            'phone': '+998901234567',
                            'role': 'user'
                        },
                        'refresh': 'refresh_token',
                        'access': 'access_token',
                        'status': 'Success'
                    }
                ),
                description='Login successful'
            ),
            401: OpenApiResponse(
                description='Authentication failed'
            )
        },
        description='Login with email and password'
    )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("User does not exist")
        
        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect password")
        
        refresh = RefreshToken.for_user(user)

        response = Response()

        response.set_cookie('refresh', str(refresh), max_age=60*60*24*365)
        response.set_cookie('access', str(refresh.access_token), max_age=60*60*24*365)

        response.data = {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "role": user.role
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "status": "Success" 
        }

        return response 
    
    @extend_schema(
        responses={200: UserSerializer},
        tags=["Users"],
        description='Get the current authenticated user information'
    )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Endpoint to retrieve the current user's information
        """
        serializer = self.get_serializer(request.user)
        data = serializer.data
        
        if request.user.is_superuser:
            data['role'] = 'admin'
        elif request.user.is_staff:
            data['role'] = 'manager'
        else:
            data['role'] = 'user'
            
        return Response(data)