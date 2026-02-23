# Step 1: Use the official AWS Lambda base image for Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Step 2: Copy your requirements file into the container
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Step 3: Install dependencies
# We use --target "${LAMBDA_TASK_ROOT}" to ensure they are in the right place for Lambda
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Step 4: Copy all your local code into the container's task root
COPY . ${LAMBDA_TASK_ROOT}

# Step 5: Set the CMD to your handler file and function name
# Format: <filename>.<function_name>
CMD [ "lambda_function.lambda_handler" ]