from django.shortcuts import render,HttpResponse,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def IndexPage(request):    
    return render(request, 'index.html')

def SignupPage(request):
    if request.method == 'POST':
        # Handle signup logic here
        uname = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')
        
        if pass1 != pass2:
            return HttpResponse("Your password and conform password do not match!")
        else:             
            my_user = User.objects.create_user(uname, email, pass1)
            my_user.save()
            return redirect('login')


    return render(request, 'signup.html')


def LoginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Login attempt for user: {username}")

        user = authenticate(request, username=username, password=password)
        print(f"Authenticated user: {user}")

        if user is not None:
            login(request, user)
            print("Login successful!")
            return redirect('index')
        else:
            print("Login failed.")
            return HttpResponse("Username or Password is incorrect!")
        

    return render(request, 'login.html')



    if request.method=='POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('password')
        user = authenticate(request, username=username, password=pass1)
        
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return HttpResponse("Username or Password is incorrect!")



    return render(request, 'login.html')


# def LogoutPage(request):
#     logout(request)
#     return redirect('login')