import secrets
import string
import uuid
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
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        user_data = {
            'username': request.data.get('fullname'),
            'email': request.data.get('email'),
            'phone': request.data.get('phone'),
            'is_legal': request.data.get('is_legal', False),
            'company_name': request.data.get('company_name'),
            'password': password,
            'role': 'client',
        }

        if not user_data['email']:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_data['phone']:
            return Response({'error': 'Phone is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        announcement_data = request.data.get('announcement', {})
        announcement_data['client_id'] = user.id
        announcement_data['status'] = 'pending'

        announcement_serializer = AnnouncementSerializer(data=announcement_data)
        announcement_serializer.is_valid(raise_exception=True)
        announcement = announcement_serializer.save()

        # Generate a temporary upload key
        upload_key = str(uuid.uuid4())

        # Optionally store the upload key in the database or cache with an expiration
        # For simplicity, we'll just return it for now

        login_url = 'http://localhost:3000/login'
        try:
            send_mail(
                subject='Your KompXizmat Account Password',
                message=(
                    f"Assalomu alaykum, {user.username}!\n\n"
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
            print(f"Failed to send email: {e}")

        return Response({
            'user': UserSerializer(user).data,
            'announcement': AnnouncementSerializer(announcement).data,
            'upload_key': upload_key,  # Include the upload key
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
        
        if request.user.role == 'admin':
            data['role'] = 'admin'
        elif request.user.role == 'manager':
            data['role'] = 'manager'
        else:
            data['role'] = 'client'
            
        return Response(data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {'error': 'Current password and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 4:
            return Response(
                {'error': 'New password must be at least 4 characters long.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.password = make_password(new_password)
        user.save()

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                'message': 'Password changed successfully',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK
        )
        response.set_cookie('refresh', str(refresh), max_age=60*60*24*365)
        response.set_cookie('access', str(refresh.access_token), max_age=60*60*24*365)

        return response

    @extend_schema(
        request=OpenApiExample(
            'Update Profile Request',
            value={
                'fullname': 'John Doe Updated',
                'email': 'updated@example.com',
                'phone': '+998901234567',
                'is_legal': False,
                'company_name': 'Updated Company'
            },
            request_only=True,
        ),
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description='Invalid data'),
            403: OpenApiResponse(description='Permission denied')
        },
        tags=["Users"],
        description='Update the current user\'s profile information'
    )
    @action(detail=False, methods=['put'], permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        user = request.user
        data = request.data

        # Update only allowed fields
        update_data = {
            'username': data.get('username', user.username),
            'email': data.get('email', user.email),
            'phone': data.get('phone', user.phone),
            'is_legal': data.get('is_legal', user.is_legal),
            'company_name': data.get('company_name', user.company_name) if user.is_legal else user.company_name,
        }

        serializer = UserSerializer(user, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

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