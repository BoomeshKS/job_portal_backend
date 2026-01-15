from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import *
from rest_framework import status
from django.contrib.auth.models import User
from .models import Job
import requests

@api_view(['GET'])
def home(request):
    return Response({'hello': 'world'})

@api_view(['POST'])
def register_user(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if User.objects.filter(username=username).exists():
        return Response(
            {"message": "User already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=username,
        password=password  # 🔐 auto-hashed
    )

    return Response(
        {"message": "User registered successfully"},
        status=status.HTTP_201_CREATED
    )

from django.contrib.auth import authenticate


@api_view(['POST'])
def basic_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"message": "Invalid credentials"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {
            "user_id": user.id,
            "username": user.username,
            "message": "Login successful"
        },
        status=status.HTTP_200_OK
    )

from django.conf import settings

@api_view(['GET']) 
def job_list(request): 
    jobs = Job.objects.all() 
    serializer = JobSerializer(jobs, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
def fetch_jooble_jobs(request):
    keywords = request.data.get("keywords")

    if not keywords:
        return Response(
            {"message": "keywords is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 🔥 STEP 1: CLEAR OLD JOBS
    Job.objects.all().delete()

    url = f"https://jooble.org/api/{settings.JOOBLE_API_KEY}"

    payload = {
        "keywords": keywords,
        "location": "india"
    }

    response = requests.post(url, json=payload)

    if response.status_code != 200:
        return Response(
            {"message": "Failed to fetch jobs"},
            status=status.HTTP_400_BAD_REQUEST
        )

    jobs = response.json().get("jobs", [])
    system_user = User.objects.first()

    for job in jobs:
        Job.objects.create(
            title=job.get("title", "")[:200],
            description=job.get("snippet", ""),
            company=job.get("company", "Unknown"),
            location=job.get("location", "India"),
            salary_range=job.get("salary", ""),
            apply_link=job.get("link", ""),
            created_by=system_user
        )

    return Response(
        {
            "message": "Jobs refreshed successfully",
            "keyword": keywords,
            "total_jobs": len(jobs)
        },
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def job_detail(request, id):
    try:
        job = Job.objects.get(id=id)
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = JobSerializer(job)
    return Response(serializer.data)


@api_view(['POST'])
def apply_job(request):
    serializer = ApplicationSerializer(data=request.data)
    job_id = request.data.get('job')
    applicant_id = request.data.get('applicant')
    # Check
    if Application.objects.filter(job_id=job_id, applicant_id=applicant_id).exists():
        return Response({"message":"You have already applied for this job"}, status=status.HTTP_400_BAD_REQUEST)
    if serializer.is_valid():
        serializer.save()
        return Response({"message":"Application Submitted Successfully"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def my_applications(request, user_id):
    applications = Application.objects.filter(applicant_id=user_id).select_related("job")

    data = []
    for app in applications:
        data.append({
            "application_id": app.id,
            "status": app.status,
            "applied_on": app.applied_on,
            "job": {
                "id": app.job.id,
                "title": app.job.title,
                "company": app.job.company,
                "location": app.job.location,
                "salary_range": app.job.salary_range,
            }
        })

    return Response(data)
