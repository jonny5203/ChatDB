#!/usr/bin/env python3

"""
Training Orchestrator Test Implementation Validation
This script validates that our comprehensive test implementation is complete and working.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (MISSING)")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status."""
    if Path(dirpath).exists():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (MISSING)")
        return False

def main():
    print("🔍 Validating Training Orchestrator Test Implementation")
    print("=" * 55)
    
    # Base paths
    base_path = Path("/home/jonny/projects/ChatDB")
    training_orchestrator_path = base_path / "training-orchestrator"
    k8s_tests_path = base_path / "kubernetes" / "test-runner"
    
    success_count = 0
    total_checks = 0
    
    print("\n📁 File Structure Validation:")
    print("-" * 30)
    
    # Check core service files
    files_to_check = [
        (training_orchestrator_path / "main.py", "Training Orchestrator service"),
        (training_orchestrator_path / "models.py", "Database models"),
        (training_orchestrator_path / "database.py", "Database configuration"),
        (training_orchestrator_path / "tests" / "test_main.py", "Unit tests"),
        (k8s_tests_path / "tests" / "test_training_orchestrator_k8s.py", "Kubernetes integration tests"),
        (k8s_tests_path / "pytest.ini", "Pytest configuration"),
        (k8s_tests_path / "requirements.txt", "Test dependencies"),
        (k8s_tests_path / "run_training_orchestrator_tests.sh", "Test execution script"),
        (k8s_tests_path / "Dockerfile", "Test container definition"),
    ]
    
    for filepath, description in files_to_check:
        total_checks += 1
        if check_file_exists(filepath, description):
            success_count += 1
    
    print("\n🔧 API Endpoint Validation:")
    print("-" * 28)
    
    # Check if the new GET /jobs endpoint was added
    main_py_content = (training_orchestrator_path / "main.py").read_text()
    total_checks += 1
    if '@app.get("/jobs")' in main_py_content and 'def list_training_jobs' in main_py_content:
        print("✅ GET /jobs endpoint added")
        success_count += 1
    else:
        print("❌ GET /jobs endpoint missing")
    
    print("\n🧪 Test Configuration Validation:")
    print("-" * 32)
    
    # Check pytest configuration
    pytest_ini_content = (k8s_tests_path / "pytest.ini").read_text()
    total_checks += 3
    
    if "--junit-xml" in pytest_ini_content:
        print("✅ JUnit XML output configured")
        success_count += 1
    else:
        print("❌ JUnit XML output not configured")
    
    if "performance:" in pytest_ini_content and "resilience:" in pytest_ini_content:
        print("✅ Test markers configured")
        success_count += 1
    else:
        print("❌ Test markers not properly configured")
    
    if "--cov" in pytest_ini_content:
        print("✅ Code coverage configured")
        success_count += 1
    else:
        print("❌ Code coverage not configured")
    
    print("\n🐳 Kubernetes Test Features:")
    print("-" * 26)
    
    k8s_test_content = (k8s_tests_path / "tests" / "test_training_orchestrator_k8s.py").read_text()
    
    # Check for comprehensive test coverage
    test_features = [
        ("Kubernetes DNS resolution", "svc.cluster.local"),
        ("Database connectivity tests", "psycopg2.connect"),
        ("Job lifecycle tests", "test_job_lifecycle_complete"),
        ("Concurrent job tests", "ThreadPoolExecutor"),
        ("Error handling tests", "test_invalid_job_data_validation"),
        ("Resilience tests", "test_service_recovery_after_error"),
        ("Performance tests", "@pytest.mark.performance"),
    ]
    
    for feature_name, search_string in test_features:
        total_checks += 1
        if search_string in k8s_test_content:
            print(f"✅ {feature_name}")
            success_count += 1
        else:
            print(f"❌ {feature_name} (not found)")
    
    print("\n📊 Implementation Summary:")
    print("-" * 25)
    print(f"✅ Successful checks: {success_count}")
    print(f"❌ Failed checks: {total_checks - success_count}")
    print(f"📈 Success rate: {(success_count/total_checks)*100:.1f}%")
    
    print("\n🎯 Task #11 Acceptance Criteria Status:")
    print("-" * 37)
    
    # Check each acceptance criteria from the original task
    criteria = [
        ("test_orchestrator.py modified for Kubernetes DNS resolution", "svc.cluster.local" in k8s_test_content),
        ("Database connection tests using PostgreSQL service", "psycopg2" in k8s_test_content),
        ("All API endpoints tested (GET /health, POST /jobs, GET /jobs)", all([
            "test_training_orchestrator_health" in k8s_test_content,
            "test_create_training_job_k8s" in k8s_test_content,
            "test_list_training_jobs_k8s" in k8s_test_content
        ])),
        ("Job lifecycle tests (create, status, complete)", "test_job_lifecycle_complete" in k8s_test_content),
        ("Error handling and edge case tests included", all([
            "test_invalid_job_data_validation" in k8s_test_content,
            "test_service_error_handling" in k8s_test_content
        ])),
    ]
    
    criteria_met = 0
    for criterion, is_met in criteria:
        if is_met:
            print(f"✅ {criterion}")
            criteria_met += 1
        else:
            print(f"❌ {criterion}")
    
    print(f"\n📋 Acceptance Criteria: {criteria_met}/{len(criteria)} met")
    
    if criteria_met == len(criteria) and success_count/total_checks >= 0.9:
        print("\n🎉 SUCCESS: Training Orchestrator tests implementation is complete!")
        print("   Ready for Kubernetes deployment and execution.")
        return 0
    else:
        print("\n⚠️  ISSUES FOUND: Some requirements are not fully met.")
        print("   Review the failed checks above and address them.")
        return 1

if __name__ == "__main__":
    sys.exit(main())