# Use a specialized image with both Python and Node.js
FROM nikolaik/python-nodejs:python3.11-nodejs20

WORKDIR /app

# Copy dependency files first for caching
COPY requirements.txt .
COPY package.json .
COPY frontend/package.json ./frontend/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies for both root and frontend
RUN npm install
RUN cd frontend && npm install

# Copy the rest of the application
COPY . .

# Build the frontend
RUN cd frontend && npm run build

# Expose the port (Railway provides this via $PORT)
ENV PORT=8001
EXPOSE 8001

# Command to run the backend (which serves the built frontend)
CMD ["sh", "-c", "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
