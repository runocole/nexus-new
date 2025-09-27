from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, generics
from django.contrib.auth import get_user_model
from authentication.models import User, PasswordResetToken, EmailVerificationCode
from authentication.serializers import (
    UserSerializer,
    ChangePasswordSerializer,
    MyTokenObtainPairSerializer,
    EmailUsernameTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetVerifySerializer,
    UserProfileSerializer,
    EmailVerificationRequestSerializer,
    EmailVerificationConfirmSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class EmailUsernameTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailUsernameTokenObtainPairSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(is_active=False)  # Require email verification
        password = serializer.validated_data.get('password')
        user.set_password(password)
        user.save()
        # create verification code
        EmailVerificationCode.objects.create(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)

        return Response({
            "message": "User created successfully. Please verify your email to activate your account."
        }, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.update(request.user, serializer.validated_data)
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email__iexact=email)

        reset_token = PasswordResetToken.objects.create(user=user)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')

        from .email_utils import send_password_reset_email
        try:
            send_password_reset_email(user, reset_token.token, frontend_url)
            return Response({
                "message": "Password reset email sent successfully",
                "email": email
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send password reset email: {str(e)}")

            return Response({
                "error": "Failed to send password reset email",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetVerifyView(generics.GenericAPIView):
    serializer_class = PasswordResetVerifySerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        token_obj = PasswordResetToken.objects.get(token=token)

        return Response({
            "message": "Token is valid",
            "user_id": str(token_obj.user.id),
            "email": token_obj.user.email,
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        token_obj = PasswordResetToken.objects.get(token=token)
        user = token_obj.user

        user.set_password(new_password)
        user.save()

        token_obj.used = True
        token_obj.save()

        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        return Response({
            "message": "Password has been reset successfully"
        }, status=status.HTTP_200_OK)


class EmailVerificationRequestView(generics.GenericAPIView):
    serializer_class = EmailVerificationRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.get(email=email)
        if user.is_active:
            return Response({"message": "User already verified"}, status=status.HTTP_200_OK)

        verification = EmailVerificationCode.objects.create(user=user)

        from .email_utils import send_verification_email
        send_verification_email(user, verification.code)

        return Response({"message": "Verification code sent"}, status=status.HTTP_200_OK)


class EmailVerificationConfirmView(generics.GenericAPIView):
    serializer_class = EmailVerificationConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        user = User.objects.get(email=email)
        verification = EmailVerificationCode.objects.filter(user=user, code=code, used=False).last()

        if not verification or not verification.is_valid():
            return Response({"error": "Invalid or expired code"}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()
        verification.used = True
        verification.save()

        return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)
