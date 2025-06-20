#!/bin/bash

# Legal RAG Agent - Test Runner Script
# This script runs comprehensive tests for the Legal RAG Agent project

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="legalrag"
TEST_COMPOSE_FILE="docker-compose.test.yml"
RESULTS_DIR="./test-results"

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo " Legal RAG Agent - Automated Test Suite"
    echo "=============================================="
    echo -e "${NC}"
}

print_step() {
    echo -e "${YELLOW}► $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

cleanup() {
    print_step "Cleaning up test environment..."
    docker-compose -f $TEST_COMPOSE_FILE down --volumes --remove-orphans 2>/dev/null || true
    print_success "Cleanup completed"
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    print_success "All dependencies are available"
}

prepare_environment() {
    print_step "Preparing test environment..."
    
    # Create results directory
    mkdir -p $RESULTS_DIR
    
    # Clean any existing test containers
    cleanup
    
    print_success "Test environment prepared"
}

build_test_images() {
    print_step "Building test images..."
    
    if docker-compose -f $TEST_COMPOSE_FILE build test-runner; then
        print_success "Test images built successfully"
    else
        print_error "Failed to build test images"
        exit 1
    fi
}

start_test_services() {
    print_step "Starting test services..."
    
    # Start database and other dependencies
    docker-compose -f $TEST_COMPOSE_FILE up -d test-db test-redis test-weaviate test-t2v-transformers
    
    print_step "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are healthy
    if docker-compose -f $TEST_COMPOSE_FILE exec -T test-db pg_isready -U test_user -d legalrag_test > /dev/null 2>&1; then
        print_success "Database is ready"
    else
        print_error "Database failed to start"
        exit 1
    fi
    
    if docker-compose -f $TEST_COMPOSE_FILE exec -T test-redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_error "Redis failed to start"
        exit 1
    fi
    
    print_success "All test services are ready"
}

run_unit_tests() {
    print_step "Running unit tests..."
    
    if docker-compose -f $TEST_COMPOSE_FILE run --rm test-runner \
        pytest -m unit --cov=app --cov-report=xml:/app/test-results/unit-coverage.xml \
        --junit-xml=/app/test-results/unit-results.xml -v; then
        print_success "Unit tests passed"
        return 0
    else
        print_error "Unit tests failed"
        return 1
    fi
}

run_integration_tests() {
    print_step "Running integration tests..."
    
    if docker-compose -f $TEST_COMPOSE_FILE run --rm test-runner \
        pytest -m integration --junit-xml=/app/test-results/integration-results.xml -v; then
        print_success "Integration tests passed"
        return 0
    else
        print_error "Integration tests failed"
        return 1
    fi
}

run_api_tests() {
    print_step "Running API tests..."
    
    if docker-compose -f $TEST_COMPOSE_FILE run --rm test-runner \
        pytest -m api --junit-xml=/app/test-results/api-results.xml -v; then
        print_success "API tests passed"
        return 0
    else
        print_error "API tests failed"
        return 1
    fi
}

run_all_tests() {
    print_step "Running complete test suite..."
    
    if docker-compose -f $TEST_COMPOSE_FILE run --rm test-runner \
        pytest --cov=app --cov-report=html:/app/test-results/htmlcov \
        --cov-report=xml:/app/test-results/coverage.xml \
        --junit-xml=/app/test-results/junit.xml \
        --cov-fail-under=80 -v; then
        print_success "All tests passed"
        return 0
    else
        print_error "Some tests failed"
        return 1
    fi
}

generate_report() {
    print_step "Generating test report..."
    
    echo "# Test Results Summary" > $RESULTS_DIR/summary.md
    echo "Generated on: $(date)" >> $RESULTS_DIR/summary.md
    echo "" >> $RESULTS_DIR/summary.md
    
    if [ -f "$RESULTS_DIR/junit.xml" ]; then
        # Parse test results from JUnit XML (basic parsing)
        total_tests=$(grep -o 'tests="[0-9]*"' $RESULTS_DIR/junit.xml | cut -d'"' -f2)
        failed_tests=$(grep -o 'failures="[0-9]*"' $RESULTS_DIR/junit.xml | cut -d'"' -f2)
        error_tests=$(grep -o 'errors="[0-9]*"' $RESULTS_DIR/junit.xml | cut -d'"' -f2)
        
        echo "## Test Statistics" >> $RESULTS_DIR/summary.md
        echo "- Total Tests: ${total_tests:-0}" >> $RESULTS_DIR/summary.md
        echo "- Failed Tests: ${failed_tests:-0}" >> $RESULTS_DIR/summary.md
        echo "- Error Tests: ${error_tests:-0}" >> $RESULTS_DIR/summary.md
        echo "" >> $RESULTS_DIR/summary.md
    fi
    
    if [ -f "$RESULTS_DIR/coverage.xml" ]; then
        # Extract coverage information
        coverage=$(grep -o 'line-rate="[0-9.]*"' $RESULTS_DIR/coverage.xml | head -1 | cut -d'"' -f2)
        coverage_percent=$(echo "$coverage * 100" | bc -l 2>/dev/null || echo "N/A")
        
        echo "## Coverage" >> $RESULTS_DIR/summary.md
        echo "- Line Coverage: ${coverage_percent}%" >> $RESULTS_DIR/summary.md
        echo "" >> $RESULTS_DIR/summary.md
    fi
    
    echo "## Reports Available" >> $RESULTS_DIR/summary.md
    echo "- HTML Coverage Report: \`test-results/htmlcov/index.html\`" >> $RESULTS_DIR/summary.md
    echo "- JUnit XML Report: \`test-results/junit.xml\`" >> $RESULTS_DIR/summary.md
    echo "- Coverage XML Report: \`test-results/coverage.xml\`" >> $RESULTS_DIR/summary.md
    
    print_success "Test report generated at $RESULTS_DIR/summary.md"
}

show_results() {
    print_step "Test Results Summary:"
    
    if [ -f "$RESULTS_DIR/summary.md" ]; then
        cat $RESULTS_DIR/summary.md
    fi
    
    echo ""
    echo "📊 Detailed reports available in: $RESULTS_DIR/"
    echo "🌐 Open $RESULTS_DIR/htmlcov/index.html to view coverage report"
}

# Main execution
main() {
    print_header
    
    # Parse command line arguments
    TEST_TYPE=${1:-all}
    
    case $TEST_TYPE in
        "unit")
            echo "Running unit tests only..."
            ;;
        "integration") 
            echo "Running integration tests only..."
            ;;
        "api")
            echo "Running API tests only..."
            ;;
        "all")
            echo "Running complete test suite..."
            ;;
        *)
            echo "Usage: $0 [unit|integration|api|all]"
            echo "Default: all"
            exit 1
            ;;
    esac
    
    # Set up signal handlers for cleanup
    trap cleanup EXIT
    trap cleanup INT
    
    # Run test pipeline
    check_dependencies
    prepare_environment
    build_test_images
    start_test_services
    
    # Run tests based on type
    test_result=0
    case $TEST_TYPE in
        "unit")
            run_unit_tests || test_result=1
            ;;
        "integration")
            run_integration_tests || test_result=1
            ;;
        "api")
            run_api_tests || test_result=1
            ;;
        "all")
            run_all_tests || test_result=1
            ;;
    esac
    
    # Generate reports
    generate_report
    show_results
    
    # Final status
    if [ $test_result -eq 0 ]; then
        print_success "All tests completed successfully! 🎉"
        exit 0
    else
        print_error "Some tests failed. Please check the reports for details."
        exit 1
    fi
}

# Run main function with all arguments
main "$@" 