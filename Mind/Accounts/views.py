from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from .models import UserProfile
from .serializers import UserSerializer
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AppUser
@login_required
def index(request):
    return render(request, 'index.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'accounts:index')
            return redirect(next_url)
        else:
            return render(request, 'login.html', {'form': {'errors': True}})

    return render(request, 'login.html')

class ProfileView(APIView):
    def get(self, request):
        print(request)
        user = request.user
        serializer = UserSerializer(user,context={'request':request})
        return Response(serializer.data)


    def put(self, request):
        print(request)
        user = request.user
        serializer = UserSerializer(user, data=request.data, context={'request':request})
        if serializer.is_valid():
            serializer.save()
        
            return Response(serializer.data)
        
        return Response(serializer.errors, status=400)