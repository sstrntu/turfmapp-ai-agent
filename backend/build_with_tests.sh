#!/bin/bash
# Safe Docker build with comprehensive testing

set -e  # Exit on any error

echo "🐳 SAFE DOCKER BUILD WITH COMPREHENSIVE TESTING"
echo "================================================"
echo ""
echo "This build will:"
echo "✅ Run regression tests (ensure nothing broke)"
echo "✅ Run unit tests (test individual components)"
echo "✅ Run integration tests (test service interactions)" 
echo "✅ Run API tests (test endpoints)"
echo "✅ Verify 35%+ test coverage"
echo "❌ FAIL THE BUILD if any test fails"
echo ""
echo "🔒 This prevents broken code from reaching production!"
echo ""

# Ask for confirmation
read -p "Continue with safe build? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Build cancelled."
    exit 1
fi

echo ""
echo "🚀 Starting Docker build..."
echo ""

# Build with comprehensive testing
if docker build -t turfmapp-backend . --no-cache; then
    echo ""
    echo "🎉 SUCCESS! Docker build completed with all tests passing."
    echo ""
    echo "📊 What was tested:"
    echo "   ✅ Regression tests - Core functionality works"
    echo "   ✅ Unit tests - Individual components work"
    echo "   ✅ Integration tests - Services work together"
    echo "   ✅ API tests - Endpoints respond correctly"
    echo "   ✅ Coverage - 35%+ of code is tested"
    echo ""
    echo "🔒 Your code is SAFE to deploy!"
    echo ""
    echo "Next steps:"
    echo "1. docker run -p 8000:8000 turfmapp-backend  # Test locally"
    echo "2. docker push your-registry/turfmapp-backend  # Deploy"
    echo ""
else
    echo ""
    echo "❌ BUILD FAILED!"
    echo ""
    echo "This is GOOD! The build caught problems before deployment."
    echo ""
    echo "🔍 Common issues:"
    echo "• Regression test failed - You broke existing functionality"
    echo "• Unit test failed - New code has bugs"
    echo "• Integration test failed - Services don't work together"
    echo "• Coverage too low - Add more tests"
    echo ""
    echo "📋 To debug:"
    echo "1. ./run_tests.sh  # Run tests locally to see details"
    echo "2. Fix the failing tests"
    echo "3. Run this build script again"
    echo ""
    exit 1
fi