import { GraphQLClient } from 'graphql-request';
import * as Dom from 'graphql-request/dist/types.dom';
import gql from 'graphql-tag';
export type Maybe<T> = T | null;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: string;
  String: string;
  Boolean: boolean;
  Int: number;
  Float: number;
  JsonDiff: any;
  Key: any;
  Reply: any;
  SerializedEntity: any;
  Token: any;
};

export type Credentials = {
  username: Scalars['String'];
  password: Scalars['String'];
};

export type EntitiesUpdated = {
  __typename?: 'EntitiesUpdated';
  affected: Scalars['Int'];
};

export type EntityDiff = {
  key: Scalars['String'];
  serialized: Scalars['String'];
};

export type Evaluation = {
  __typename?: 'Evaluation';
  reply: Scalars['Reply'];
  entities?: Maybe<Array<KeyedEntity>>;
};



export type KeyedEntity = {
  __typename?: 'KeyedEntity';
  key: Scalars['String'];
  serialized: Scalars['SerializedEntity'];
  diff?: Maybe<Scalars['JsonDiff']>;
};

export type LanguageQueryCriteria = {
  text: Scalars['String'];
  evaluator: Scalars['Key'];
  persistence?: Maybe<PersistenceCriteria>;
};

export type Mutation = {
  __typename?: 'Mutation';
  login: Scalars['Token'];
  makeSample?: Maybe<EntitiesUpdated>;
  update?: Maybe<EntitiesUpdated>;
  language: Evaluation;
};


export type MutationLoginArgs = {
  credentials: Credentials;
};


export type MutationUpdateArgs = {
  entities?: Maybe<Array<EntityDiff>>;
};


export type MutationLanguageArgs = {
  criteria: LanguageQueryCriteria;
};

export type PersistenceCriteria = {
  read: Scalars['String'];
  write: Scalars['String'];
};

export type Query = {
  __typename?: 'Query';
  size: Scalars['Int'];
  world: KeyedEntity;
  entitiesByKey?: Maybe<Array<KeyedEntity>>;
  entitiesByGid?: Maybe<Array<KeyedEntity>>;
  areas?: Maybe<Array<KeyedEntity>>;
  people?: Maybe<Array<KeyedEntity>>;
};


export type QueryEntitiesByKeyArgs = {
  key?: Maybe<Scalars['Key']>;
  identities?: Maybe<Scalars['Boolean']>;
};


export type QueryEntitiesByGidArgs = {
  gid?: Maybe<Scalars['Int']>;
  identities?: Maybe<Scalars['Boolean']>;
};




export type LoginMutationVariables = Exact<{
  username: Scalars['String'];
  password: Scalars['String'];
}>;


export type LoginMutation = (
  { __typename?: 'Mutation' }
  & Pick<Mutation, 'login'>
);


export const LoginDocument = gql`
    mutation login($username: String!, $password: String!) {
  login(credentials: {username: $username, password: $password})
}
    `;

export type SdkFunctionWrapper = <T>(action: (requestHeaders?:Record<string, string>) => Promise<T>, operationName: string) => Promise<T>;


const defaultWrapper: SdkFunctionWrapper = (action, _operationName) => action();

export function getSdk(client: GraphQLClient, withWrapper: SdkFunctionWrapper = defaultWrapper) {
  return {
    login(variables: LoginMutationVariables, requestHeaders?: Dom.RequestInit["headers"]): Promise<LoginMutation> {
      return withWrapper((wrappedRequestHeaders) => client.request<LoginMutation>(LoginDocument, variables, {...requestHeaders, ...wrappedRequestHeaders}), 'login');
    }
  };
}
export type Sdk = ReturnType<typeof getSdk>;