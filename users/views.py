import secrets
import string
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from users.models import User
from users.serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from application.models import Announcement
from application.serializers import AnnouncementSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

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
                    'fullname': 'John Doe',
                    'phone': '+998901234567',
                    'is_legal': False,
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
        request={
            'fullname': {'type': 'string'},
            'email': {'type': 'string'},
            'phone': {'type': 'string'},
            'is_legal': {'type': 'boolean'},
            'announcement': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'district': {'type': 'string'},
                    'service_type': {'type': 'string'}
                }
            }
        },
        responses={
            201: OpenApiResponse(description='User registered and announcement created'),
            400: OpenApiResponse(description='Invalid data')
        },
        description='Register a new user and create an announcement, sending password via email',
        tags=["Users"],
        examples=[
            OpenApiExample(
                'Register and Announce Example',
                value={
                    'fullname': 'John Doe',
                    'email': 'user@example.com',
                    'phone': '+998901234567',
                    'is_legal': False,
                    'announcement': {
                        'title': 'Buyurtma: Uskuna - John Doe',
                        'description': 'Kompyuterim ishlamayapti',
                        'district': 'Toshkent',
                        'service_type': 'hardware'
                    }
                },
                request_only=True,
            )
        ]
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register_and_announce(self, request):
        # Generate a random password
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Prepare user data
        user_data = {
            'fullname': request.data.get('fullname'),
            'email': request.data.get('email'),
            'phone': request.data.get('phone'),
            'is_legal': request.data.get('is_legal', False),
            'password': password,
            'role': 'client',
            'username': request.data.get('email'),  # Use email as username
        }

        # Validate and create user
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Prepare announcement data
        announcement_data = request.data.get('announcement', {})
        announcement_data['client'] = user.id
        announcement_data['status'] = 'pending'

        # Create announcement
        announcement_serializer = AnnouncementSerializer(data=announcement_data)
        announcement_serializer.is_valid(raise_exception=True)
        announcement = announcement_serializer.save()

        # Send email with password and login link
        login_url = 'http://localhost:3000/login'  # Replace with your frontend login URL
        try:
            send_mail(
                subject='Your KompXizmat Account Password',
                message=(
                    f"Assalomu alaykum, {user.fullname}!\n\n"
                    f"Siz KompXizmat platformasida muvaffaqiyatli ro‘yxatdan o‘tdingiz.\n"
                    f"Sizning email: {user.email}\n"
                    f"Sizning parolingiz: {password}\n\n"
                    f"Tizimga kirish uchun quyidagi havoladan foydalaning:\n{login_url}\n\n"
                    f"Iltimos, parolingizni xavfsiz saqlang va xavfsizlik uchun uni o‘zgartiring."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't fail the registration
            print(f"Failed to send email: {e}")

        return Response({
            'user': UserSerializer(user).data,
            'announcement': AnnouncementSerializer(announcement).data
        }, status=status.HTTP_201_CREATED)

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
                            'role': 'client'
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
        serializer = self.get_serializer(request.user)
        data = serializer.data
        
        if request.user.is_superuser:
            data['role'] = 'admin'
        elif request.user.is_staff:
            data['role'] = 'manager'
        else:
            data['role'] = 'client'
            
        return Response(data)

    @extend_schema(
        responses={200: UserSerializer(many=True)},
        tags=["Users"],
        description="Get all users (admin only)"
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def all_users(self, request):
        if not request.user.role == 'admin':
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)