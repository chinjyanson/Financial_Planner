#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /code

# Removes output stream buffering, allowing for more efficient logging
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the working directory contents into the container at /code
COPY . /code/

# NOTE: not needed
# EXPOSE 8080

# Set the command to use fastapi run, which uses Uvicorn underneath
# run from the current working directory
# should point to file where FastAPI is initialized, i.e., app = FastAPI() 
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
# CMD ["uvicorn", "components.fastapi_test:app", "--host", "0.0.0.0", "--port", "8080"]


CMD ["uvicorn", "components.fastapi_test:app", "--host", "0.0.0.0", "--port", "8080"]

# alternative: doesnt work
# CMD ["fastapi", "run", "main.py", "--port", "80"]