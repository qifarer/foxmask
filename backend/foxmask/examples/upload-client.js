import { ApolloClient, InMemoryCache, gql, HttpLink } from '@apollo/client/core';

const client = new ApolloClient({
  link: new HttpLink({ uri: '/graphql' }),
  cache: new InMemoryCache(),
});

const CHUNK_SIZE = 10 * 1024 * 1024;

async function getFilesFromDirectory(directoryEntry, basePath = '') {
  const files = [];
  const reader = directoryEntry.createReader();
  return new Promise((resolve, reject) => {
    const readEntries = () => {
      reader.readEntries(async (entries) => {
        if (entries.length === 0) return resolve(files);
        for (const entry of entries) {
          if (entry.isFile) {
            const file = await new Promise((res) => entry.file(res));
            files.push({
              file,
              relativePath: `${basePath}${entry.name}`,
              originalPath: entry.fullPath,
            });
          } else if (entry.isDirectory) {
            const subFiles = await getFilesFromDirectory(entry, `${basePath}${entry.name}/`);
            files.push(...subFiles);
          }
        }
        readEntries();
      }, reject);
    };
    readEntries();
  });
}

const CREATE_TASK = gql`
  mutation CreateUploadTask($input: UploadTaskInput!) {
    createUploadTask(input: $input) {
      id
      baseUploadPath
    }
  }
`;

const ADD_FILES = gql`
  mutation AddFilesToUploadTask($taskId: String!, $files: [UploadFileInfoInput!]!) {
    addFilesToUploadTask(taskId: $taskId, files: $files) {
      fileId
      storagePath
      totalChunks
    }
  }
`;

const INITIATE_FILE = gql`
  mutation InitiateUploadForFile($taskId: String!, $fileId: String!) {
    initiateUploadForFile(taskId: $taskId, fileId: $fileId)
  }
`;

const UPLOAD_CHUNK = gql`
  mutation UploadFileChunk($taskId: String!, $fileId: String!, $chunkInput: UploadChunkInput!, $chunk: Upload!) {
    uploadFileChunk(taskId: $taskId, fileId: $fileId, chunkInput: $chunkInput, chunk: $chunk)
  }
`;

const COMPLETE_FILE = gql`
  mutation CompleteFileUpload($taskId: String!, $fileId: String!) {
    completeFileUpload(taskId: $taskId, fileId: $fileId)
  }
`;

async function uploadFile(taskId, fileInfo, file) {
  const { data: { initiateUploadForFile: uploadId } } = await client.mutate({
    mutation: INITIATE_FILE,
    variables: { taskId, fileId: fileInfo.fileId },
  });

  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const chunkInput = {
      chunkNumber: i + 1,
      chunkSize: end - start,
      startByte: start,
      endByte: end - 1,
      isFinalChunk: i === totalChunks - 1,
    };

    await client.mutate({
      mutation: UPLOAD_CHUNK,
      variables: { taskId, fileId: fileInfo.fileId, chunkInput, chunk },
    });
  }

  await client.mutate({
    mutation: COMPLETE_FILE,
    variables: { taskId, fileId: fileInfo.fileId },
  });
}

async function upload(sourcePathsOrFiles, sourceType = 'single_file', preserveStructure = true) {
  let filesToUpload = [];
  if (sourceType.includes('directory')) {
    for (const path of sourcePathsOrFiles) {
      const files = await getFilesFromDirectory(path);
      filesToUpload.push(...files);
    }
  } else {
    filesToUpload = sourcePathsOrFiles.map(file => ({ file, relativePath: file.name, originalPath: file.webkitRelativePath || file.name }));
  }

  const input = {
    taskType: 'FILE_UPLOAD',
    sourceType,
    sourcePaths: filesToUpload.map(f => f.originalPath),
    uploadStrategy: 'SEQUENTIAL',
    chunkSize: CHUNK_SIZE,
    preserveStructure,
    autoExtractMetadata: true,
    title: `Upload Task ${new Date().toISOString()}`,
    tags: ['upload'],
  };

  const { data: { createUploadTask: { id: taskId } } } = await client.mutate({
    mutation: CREATE_TASK,
    variables: { input },
  });

  const fileInfos = filesToUpload.map(({ file, relativePath, originalPath }) => ({
    originalPath: preserveStructure ? relativePath : file.name,
    filename: file.name,
    fileSize: file.size,
    contentType: file.type,
    extension: file.name.split('.').pop(),
  }));

  const { data: { addFilesToUploadTask: addedFiles } } = await client.mutate({
    mutation: ADD_FILES,
    variables: { taskId, files: fileInfos },
  });

  for (let i = 0; i < addedFiles.length; i++) {
    await uploadFile(taskId, addedFiles[i], filesToUpload[i].file);
  }

  console.log(`Upload task ${taskId} completed`);
}